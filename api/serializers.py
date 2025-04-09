from rest_framework import serializers

class NameCorrectionRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20)
    last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=20)
    country_code = serializers.RegexField(regex=r'^[A-Za-z]{2}$', required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        """Check that at least one name is provided."""
        if not attrs.get('first_name') and not attrs.get('last_name'):
            raise serializers.ValidationError("At least one of 'first_name' or 'last_name' must be provided.")
        # Normalize country code if present
        if attrs.get('country_code'):
            attrs['country_code'] = attrs['country_code'].upper()
        return attrs
