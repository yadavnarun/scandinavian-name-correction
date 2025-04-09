# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from .apps import get_matcher_instance
from .serializers import NameCorrectionRequestSerializer

logger = logging.getLogger(__name__)

class NameCorrectionView(APIView):
    """
    API endpoint to get corrections/suggestions for Scandinavian names.
    Accepts POST requests with 'first_name', 'last_name', and 'country_code'.
    """
    def post(self, request, *args, **kwargs):
        """Handles POST request for name correction."""
        serializer = NameCorrectionRequestSerializer(data=request.data)

        if serializer.is_valid():
            validated_data = serializer.validated_data
            if not isinstance(validated_data, dict):
                logger.error("Invalid data type for validated_data: Expected dict.")
                return Response({"error": "Invalid data format."}, status=status.HTTP_400_BAD_REQUEST)
            
            first_name = validated_data.get('first_name')
            last_name = validated_data.get('last_name')
            country_code = validated_data.get('country_code')

            try:
                matcher = get_matcher_instance()
                logger.info(f"Processing request: First='{first_name}', Last='{last_name}', Country='{country_code}'")

                results = matcher.smart_search(
                    first_name=first_name,
                    last_name=last_name,
                    country_code=country_code,
                    n=15,
                    threshold=70
                )
                
                return Response(results, status=status.HTTP_200_OK)

            except RuntimeError as e:
                 logger.error(f"Matcher unavailable: {e}")
                 return Response({"error": "Name correction service is temporarily unavailable."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as e:
                 logger.exception(f"An unexpected error occurred during name correction: {e}")
                 return Response({"error": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            logger.warning(f"Invalid request data received: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)