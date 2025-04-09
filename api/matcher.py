import time
import os
import pickle
import gzip
import logging
from collections import defaultdict
from typing import List, Dict, Optional, Set, Tuple, Union # Added Union

import pycountry
from doublemetaphone import doublemetaphone
from rapidfuzz import fuzz, process
from names_dataset import NameDataset


# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants ---
# Scoring Parameters
NORDIC_NAME_BONUS = 5
COUNTRY_MATCH_BONUS = 10 #! More relevant for first names?
VARIANT_MATCH_BONUS = 15
EXACT_QUERY_VARIANT_BONUS = 20
COUNTRY_MISMATCH_PENALTY = 10
POPULAR_THRESHOLD = 0.5
RULE_VARIANT_SCORE = 75
LEXICAL_SEARCH_THRESHOLD = 70
BASE_SIMILARITY_THRESHOLD_FACTOR = 0.8

# Comprehensive Nordic Substitution Rules (Keep the dict from previous step)
COMPREHENSIVE_NORDIC_SUBSTITUTIONS = {
    "aa": {"default": "å", "countries": {"SE", "DK", "NO"}},
    "ae": [
        {"target": "æ", "countries": {"DK", "NO", "IS"}},
        {"target": "ä", "countries": {"SE", "FI"}}
    ],
    "oe": [
        {"target": "ø", "countries": {"DK", "NO"}},
        {"target": "ö", "countries": {"SE", "FI", "IS"}}
    ],
    "th": [
        {"target": "þ", "countries": {"IS"}},
        {"target": "t"} # Default simplification
    ],
    "ph": {"default": "f"},
    "ch": {"default": "k"}, # Simplest default
    "ck": {"default": "k"},
    "sch": {"default": "sk"},
    "qu": {"default": "kv"},
    "a": [
        {"target": "å", "countries": {"SE", "DK"}},
        {"target": "ä", "countries": {"SE", "FI"}},
        {"target": "á", "countries": {"IS"}}
    ],
    "o": [
        {"target": "ö", "countries": {"SE", "FI", "IS"}},
        {"target": "ø", "countries": {"DK", "NO"}},
        {"target": "ó", "countries": {"IS"}}
    ],
    "e": [{"target": "é", "countries": {"IS"}}],
    "i": [{"target": "í", "countries": {"IS"}}],
    "u": [{"target": "ú", "countries": {"IS"}}],
    "y": [{"target": "ý", "countries": {"IS"}}],
    "d": [{"target": "ð", "countries": {"IS"}}], # Often internal d->ð
    "c": ["k", "s"], # Generate BOTH 'k' and 's' variants (context hard)
    "w": {"default": "v", "exclude_countries": {"FI"}}, # Less likely replacement in Finnish
    "x": {"default": "ks"},
    "z": {"default": "s"},
}
PATTERN_SUBSTITUTIONS = {
    "go": {"SE": "gö", "DK": "gø", "NO": "gø"},
    "so": {"SE": "sö", "DK": "sø", "NO": "sø"},
    "mo": {"DK": "mø", "NO": "mø"},
}
INITIAL_SUBSTITUTIONS = { "t": {"IS": "þ"} }
NORDIC_COUNTRIES = {"SE", "DK", "NO", "IS", "FI"}

# Cache configuration
CACHE_FILENAME = "name_metaphone_cache.v1.pkl.gz"
CACHE_VERSION = 1

# --- Global Initialization (Keep as before) ---
try:
    logger.info("Initializing NameDataset...")
    ND_START_TIME = time.time()
    ND_INSTANCE = NameDataset()
    logger.info(f"NameDataset initialized in {time.time() - ND_START_TIME:.2f}s.")
except Exception as e:
    logger.error(f"Fatal Error: Failed to initialize NameDataset: {e}")
    raise SystemExit(f"Could not initialize NameDataset: {e}")

try:
    COUNTRY_CODE_MAP = {country.alpha_2: country for country in pycountry.countries}
except Exception as e:
    logger.error(f"Error initializing country code map: {e}")
    COUNTRY_CODE_MAP = {}

# --- Helper Functions ---
def validate_country_code(country_code: Optional[str]) -> Optional[str]:
    if not country_code: return None
    code = country_code.upper()
    if code in COUNTRY_CODE_MAP: return code
    logger.warning(f"Invalid country code: {country_code}")
    return None

def generate_nordic_variants(name: str, country_code: Optional[str] = None) -> Set[str]:
    if not name: return set()
    results = {name}
    original_lower = name.lower()
    country_code = validate_country_code(country_code) if country_code else None
    name_len = len(name)

    def _preserve_case(original_chars: str, replacement: str) -> str:
        if not original_chars or not replacement: return replacement
        if original_chars.istitle(): return replacement[0].upper() + replacement[1:].lower()
        if original_chars.isupper(): return replacement.upper()
        if original_chars[0].isupper() and (len(original_chars) == 1 or original_chars[1:].islower()): return replacement[0].upper() + replacement[1:].lower()
        return replacement.lower()

    processed_indices = set()
    possible_lengths = {len(k) for k in COMPREHENSIVE_NORDIC_SUBSTITUTIONS.keys()} | {1}
    for length in sorted(possible_lengths, reverse=True):
        if length > name_len: continue
        for i in range(name_len - length + 1):
            if i in processed_indices: continue
            source_chars_original = name[i : i + length]
            source_chars_lower = original_lower[i : i + length]
            if source_chars_lower in COMPREHENSIVE_NORDIC_SUBSTITUTIONS:
                sub_rule = COMPREHENSIVE_NORDIC_SUBSTITUTIONS[source_chars_lower]
                possible_replacements = []
                rules_to_process = []
                if isinstance(sub_rule, list): rules_to_process.extend(sub_rule)
                elif isinstance(sub_rule, dict): rules_to_process.append(sub_rule)
                elif isinstance(sub_rule, str): rules_to_process.append({'target': sub_rule})

                for rule_item in rules_to_process:
                    target = None; valid_for_country = True
                    if isinstance(rule_item, str): target = rule_item
                    elif isinstance(rule_item, dict):
                        target = rule_item.get("default") or rule_item.get("target")
                        countries = rule_item.get("countries"); exclude_countries = rule_item.get("exclude_countries")
                        if country_code:
                            if countries and country_code not in countries: valid_for_country = False
                            if exclude_countries and country_code in exclude_countries: valid_for_country = False
                    if valid_for_country and target: possible_replacements.append(target)

                if possible_replacements:
                    for replacement in set(possible_replacements):
                        new_variant = name[:i] + _preserve_case(source_chars_original, replacement) + name[i + length:]
                        results.add(new_variant)
                    for j in range(length): processed_indices.add(i + j)

    for i in range(name_len - 1):
        pattern_lower = original_lower[i:i+2]
        if pattern_lower in PATTERN_SUBSTITUTIONS:
            sub_map = PATTERN_SUBSTITUTIONS[pattern_lower]
            for country, replacement in sub_map.items():
                if not country_code or country_code == country:
                    original_segment = name[i:i+2]
                    new_variant = name[:i] + _preserve_case(original_segment, replacement) + name[i+2:]
                    results.add(new_variant)

    if name and name[0].lower() in INITIAL_SUBSTITUTIONS:
         first_char_lower = name[0].lower()
         if 0 not in processed_indices:
             sub_map = INITIAL_SUBSTITUTIONS.get(first_char_lower, {})
             for country, replacement in sub_map.items():
                if not country_code or country_code == country:
                     new_variant = _preserve_case(name[0], replacement) + name[1:]
                     results.add(new_variant)
    return results


# --- SmartNameMatcher Class ---
class SmartNameMatcher:
    """
    Indexes names and provides smart search for first and last names,
    considering phonetic, lexical, and Nordic variations.
    """
    def __init__(self, use_cache=True, cache_file=CACHE_FILENAME):
        logger.info("Initializing SmartNameMatcher...")
        start_time = time.time()
        self.cache_file = cache_file
        self.variant_cache: Dict[str, Set[str]] = {}
        self.metaphone_index: Dict[str, Set[str]] = defaultdict(set)
        self.name_to_metaphone: Dict[str, Tuple[str, str]] = {}
        self.name_to_info: Dict[str, Dict] = {}
        self.nordic_names: Set[str] = set()
        self.all_indexed_names: Set[str] = set()
        loaded_from_cache = False
        if use_cache: loaded_from_cache = self._load_from_cache()
        if not loaded_from_cache:
            logger.info("Building index from NameDataset...")
            self._build_index(ND_INSTANCE)
            if use_cache: self._save_to_cache()
        logger.info(f"SmartNameMatcher ready ({len(self.all_indexed_names)} names indexed). Init time: {time.time() - start_time:.2f}s.")

    # --- Cache and Index Building Methods ---
    # _load_from_cache, _save_to_cache, _build_index, _process_and_index_name
    # remain the same as in the previous 'elegant' version.
    def _load_from_cache(self) -> bool:
        if not os.path.exists(self.cache_file): return False
        logger.warning(f"Using cache: {self.cache_file}. Delete if data/rules changed (v{CACHE_VERSION}).")
        try:
            with gzip.open(self.cache_file, 'rb') as f: cache_data = pickle.load(f)
            if cache_data.get('version') != CACHE_VERSION: logger.warning("Cache version mismatch."); return False
            if not all(k in cache_data for k in ['metaphone_index', 'name_to_metaphone', 'name_to_info', 'nordic_names']): raise ValueError("Cache structure mismatch.")
            self.metaphone_index = defaultdict(set); [self.metaphone_index[code].update(names) for code, names in cache_data.get('metaphone_index', {}).items()]
            self.name_to_metaphone = cache_data.get('name_to_metaphone', {}); self.name_to_info = cache_data.get('name_to_info', {})
            self.nordic_names = set(cache_data.get('nordic_names', [])); self.all_indexed_names = set(self.name_to_metaphone.keys())
            logger.info(f"Loaded {len(self.all_indexed_names)} names from cache."); return True
        except Exception as e:
            logger.error(f"Cache load error: {e}. Rebuilding."); self._clear_indexes(); return False

    def _save_to_cache(self):
        try:
            logger.info(f"Saving index to cache: {self.cache_file}...")
            metaphone_index_list = {k: list(v) for k, v in self.metaphone_index.items()}
            cache_data = {'version': CACHE_VERSION, 'metaphone_index': metaphone_index_list, 'name_to_metaphone': self.name_to_metaphone, 'name_to_info': self.name_to_info, 'nordic_names': list(self.nordic_names)}
            with gzip.open(self.cache_file, 'wb') as f: pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info("Cache saved.");
        except Exception as e: logger.error(f"Cache save error: {e}")

    def _clear_indexes(self):
         self.metaphone_index.clear(); self.name_to_metaphone.clear(); self.name_to_info.clear();
         self.nordic_names.clear(); self.all_indexed_names.clear()

    def _build_index(self, name_dataset: NameDataset):
        self._clear_indexes()
        def process_dict(name_dict, type_label):
             count = 0; total = len(name_dict); logger.info(f"Processing {total} {type_label}s...")
             for name, info in name_dict.items(): self._process_and_index_name(name, info, type_label); count += 1; #if count % 100000 == 0: logger.info(f"  {count}/{total} {type_label}s...")
             logger.info(f"Finished processing {count} {type_label}s.")
        process_dict(name_dataset.first_names, "first_name"); process_dict(name_dataset.last_names, "last_name")
        self.all_indexed_names = set(self.name_to_metaphone.keys())

    def _process_and_index_name(self, name: str, info: Dict, type_label: str):
        if not name or not isinstance(name, str): 
            return
        name = name.strip()
        if not name: return
        try:
            metaphone = doublemetaphone(name); self.name_to_metaphone[name] = metaphone; self.name_to_info[name] = {'type': type_label, 'data': info}
            if metaphone[0]: self.metaphone_index[metaphone[0]].add(name)
            if metaphone[1] and metaphone[1] != metaphone[0]: self.metaphone_index[metaphone[1]].add(name)
            is_nordic = any(c in name for c in 'åäöæøþÅÄÖÆØÞðÐ')
            if not is_nordic and type_label == 'first_name' and isinstance(info.get('country'), dict):
                if any(info['country'].get(c, 0) > 0.1 for c in NORDIC_COUNTRIES): is_nordic = True
            if is_nordic: self.nordic_names.add(name)
        except Exception as e: logger.warning(f"Skip name '{name}': {e}", exc_info=False)


    # --- Search Logic ---
    def _get_nordic_variants_cached(self, name: str, country_code: Optional[str]) -> Set[str]:
        """Generates or retrieves cached Nordic variants for a query name."""
        cache_key = f"{name}:{country_code or ''}"
        if cache_key not in self.variant_cache:
            self.variant_cache[cache_key] = generate_nordic_variants(name, country_code)
            if len(self.variant_cache) > 1000: self.variant_cache.pop(next(iter(self.variant_cache)))
        return self.variant_cache[cache_key]

    def _get_candidates(self, query_name: str, n_lexical: int = 50) -> Set[str]:
        """Retrieves candidate names using Metaphone and lexical similarity."""
        candidates = set()
        query_metaphone = doublemetaphone(query_name)
        if query_metaphone[0]: candidates.update(self.metaphone_index.get(query_metaphone[0], set()))
        if query_metaphone[1] and query_metaphone[1] != query_metaphone[0]: candidates.update(self.metaphone_index.get(query_metaphone[1], set()))
        phonetic_count = len(candidates)
        lexical_candidates = set()
        if len(self.all_indexed_names) > 0:
            lexical_matches = process.extract(query_name, self.all_indexed_names, scorer=fuzz.WRatio, limit=n_lexical, score_cutoff=LEXICAL_SEARCH_THRESHOLD)
            lexical_candidates = {match[0] for match in lexical_matches}
            candidates.update(lexical_candidates)
        logger.debug(f"_get_candidates({query_name}): {phonetic_count} phonetic, {len(lexical_candidates)} lexical. Total: {len(candidates)}")
        return candidates


    def _score_candidate(self,
                         cand_name: str,
                         target_name_type: str, # 'first_name' or 'last_name'
                         query_variants: Set[str],
                         query_name: str,
                         country_code: Optional[str],
                         threshold: int) -> Optional[Dict]:
        """Calculates the final score for a candidate name, filtering by type."""
        if cand_name not in self.name_to_info: return None

        info = self.name_to_info[cand_name]
        # *** Filter by name type ***
        if info.get('type') != target_name_type:
            return None

        # --- Scoring logic ---
        metaphone = self.name_to_metaphone.get(cand_name, ("", ""))
        cand_name_lower = cand_name.lower()
        query_name_lower = query_name.lower()

        base_similarity = max(fuzz.ratio(cand_name_lower, qv.lower()) for qv in query_variants)

        required_base = threshold * BASE_SIMILARITY_THRESHOLD_FACTOR
        if base_similarity < required_base:
             return None

        final_score = base_similarity
        score_reasons = []
        is_nordic_name = cand_name in self.nordic_names
        is_exact_query_variant = cand_name != query_name and cand_name in query_variants

        if cand_name_lower == query_name_lower: final_score = max(100, final_score); score_reasons.append("Exact Match")
        if is_exact_query_variant: final_score += EXACT_QUERY_VARIANT_BONUS; score_reasons.append(f"+{EXACT_QUERY_VARIANT_BONUS} (Query Variant)")
        if is_nordic_name: final_score += NORDIC_NAME_BONUS; score_reasons.append(f"+{NORDIC_NAME_BONUS} (Nordic)")

        if country_code:
            data = info.get('data', {})
            name_type = info.get('type', '') # Should match target_name_type
            # Country bonus might be less relevant for last names, but apply for now
            if name_type == 'first_name' and isinstance(data.get('country'), dict):
                country_data = data['country']
                if country_code in country_data:
                    if country_data.get(country_code, 0) > POPULAR_THRESHOLD: final_score += COUNTRY_MATCH_BONUS; score_reasons.append(f"+{COUNTRY_MATCH_BONUS} (Popular:{country_code})")
                elif country_data: final_score -= COUNTRY_MISMATCH_PENALTY; score_reasons.append(f"-{COUNTRY_MISMATCH_PENALTY} (Not in {country_code})")
            elif name_type == 'nordic_variant' and data.get('country') == country_code:
                 final_score += VARIANT_MATCH_BONUS; score_reasons.append(f"+{VARIANT_MATCH_BONUS} (Dataset Variant:{country_code})")

        final_score = min(final_score, 100)

        if final_score >= threshold:
            return {
                'name': cand_name, 'score': round(final_score), 'base_similarity': round(base_similarity),
                'metaphone': metaphone, 'is_nordic': is_nordic_name, 'is_query_variant': is_exact_query_variant,
                'in_dataset': True, 'type': info.get('type', 'unknown'), 'data': info.get('data', {}),
                'score_reasons': score_reasons or ["Similarity Only"]
            }
        return None

    def _search_name_part(self,
                          query_name: str,
                          target_name_type: str, # 'first_name' or 'last_name'
                          country_code: Optional[str],
                          n: int,
                          threshold: int) -> List[Dict]:
        """Internal helper to search for a single name part (first or last)."""
        if not query_name: return []

        scored_results = []
        try:
            # 1. Generate Variants
            use_nordic_rules = country_code in NORDIC_COUNTRIES or any(c in query_name.lower() for c in "acdghklmnoprstuwxyz")
            query_variants = self._get_nordic_variants_cached(query_name, country_code) if use_nordic_rules else {query_name}

            # 2. Get Candidates (all types initially)
            candidates = self._get_candidates(query_name)

            # 3. Score Candidates (filtering by target_name_type happens inside _score_candidate)
            for cand_name in candidates:
                scored_candidate = self._score_candidate(cand_name, target_name_type, query_variants, query_name, country_code, threshold)
                if scored_candidate:
                    scored_results.append(scored_candidate)

            # 4. Add Rule-Generated Variants (if applicable and not already found)
            # Check against scored results for THIS part only
            dataset_matched_names = {res['name'] for res in scored_results}
            if use_nordic_rules and RULE_VARIANT_SCORE >= threshold:
                for qv in query_variants:
                     if qv != query_name and qv not in self.name_to_info and qv not in dataset_matched_names:
                          scored_results.append({
                              'name': qv, 'score': RULE_VARIANT_SCORE, 'base_similarity': round(fuzz.ratio(qv.lower(), query_name.lower())),
                              'metaphone': doublemetaphone(qv), 'is_nordic': True, 'is_query_variant': True, 'in_dataset': False,
                              'type': 'rule_generated_variant', # Mark type clearly
                              'data': {'source_query': query_name, 'target_type': target_name_type},
                              'score_reasons': [f"Rule-Generated ({RULE_VARIANT_SCORE} base)"]
                          })

            # 5. Sort and Limit
            scored_results.sort(key=lambda x: x['score'], reverse=True)
            return scored_results[:n]

        except Exception as e:
            logger.exception(f"Error during _search_name_part for '{query_name}' ({target_name_type}): {e}")
            return []


    def smart_search(self,
                     first_name: Optional[str] = None,
                     last_name: Optional[str] = None,
                     country_code: Optional[str] = None,
                     n: int = 10,
                     threshold: int = 75) -> Dict[str, List[Dict]]:
        """
        Performs smart search for first and/or last names separately.

        Args:
            first_name: The first name to search for (optional).
            last_name: The last name to search for (optional).
            country_code: Optional ISO 3166-1 alpha-2 country code.
            n: Max number of results *per name part*.
            threshold: Minimum final score (0-100) to include.

        Returns:
            A dictionary with keys 'first_name_matches' and 'last_name_matches',
            each containing a list of match dictionaries sorted by score.
        """
        start_search_time = time.time()
        country_code = validate_country_code(country_code)
        results = {
            "first_name_matches": [],
            "last_name_matches": []
        }

        query_desc = []
        if first_name: query_desc.append(f"First='{first_name}'")
        if last_name: query_desc.append(f"Last='{last_name}'")
        if not query_desc:
            logger.warning("Smart search called with no first or last name.")
            return results
        query_log_str = ", ".join(query_desc) + f" ({country_code or 'Any'})"


        # Search for First Name
        if first_name:
            first_name = first_name.strip()
            if first_name:
                logger.info(f"Searching for First Name: '{first_name}'...")
                results["first_name_matches"] = self._search_name_part(
                    query_name=first_name,
                    target_name_type="first_name",
                    country_code=country_code,
                    n=n,
                    threshold=threshold
                )

        # Search for Last Name
        if last_name:
            last_name = last_name.strip()
            if last_name:
                logger.info(f"Searching for Last Name: '{last_name}'...")
                results["last_name_matches"] = self._search_name_part(
                    query_name=last_name,
                    target_name_type="last_name",
                    country_code=country_code, # Pass country code for potential Nordic surname variants?
                    n=n,
                    threshold=threshold
                )

        duration = time.time() - start_search_time
        logger.info(f"Full Search ({query_log_str}) took {duration:.4f}s.")
        return results

    def get_name_details(self, name: str) -> Optional[Dict]:
        """Retrieves detailed information for a specific name if indexed."""
        if name in self.name_to_info:
            info = self.name_to_info[name]
            return {
                'name': name, 'metaphone': self.name_to_metaphone.get(name, ("", "")),
                'type': info.get('type', 'unknown'), 'is_nordic': name in self.nordic_names,
                'in_dataset': True, 'data': info.get('data', {})
            }
        logger.debug(f"Name '{name}' not found in index for get_name_details.")
        return None
