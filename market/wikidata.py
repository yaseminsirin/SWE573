"""
Wikidata integration for semantic tagging
"""
import requests
from django.conf import settings

# Configuration
SEARCH_API_URL = "https://www.wikidata.org/w/api.php"
SPARQL_API_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "TimeBankApp/1.0 (community-timebank)"


def get_entity_id(search_term):
    """Get Wikidata entity ID from search term"""
    params = {
        "action": "wbsearchentities",
        "search": search_term,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 5
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(SEARCH_API_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get("search"):
            skip_keywords = ['database', 'website', 'software', 'company', 'organization', 
                           'web service', 'online', 'application', 'platform', 'record label',
                           'brand', 'corporation', 'enterprise', 'firm', 'business']
            for match in data["search"]:
                description = match.get('description', '').lower()
                label = match.get('label', '').lower()
                search_lower = search_term.lower()
                
                skip_descriptions = skip_keywords + ['video game', 'film', 'movie', 'album', 'song', 
                                                    'television', 'TV series', 'band', 'musical']
                if any(keyword in description for keyword in skip_descriptions):
                    continue
                
                if label == search_lower:
                    return match["id"]
                
                label_words = label.split()
                search_words = search_lower.split()
                if len(search_words) == 1 and len(label_words) > 1:
                    continue
                
                if search_lower in label:
                    return match["id"]
            
            best_match = data["search"][0]
            return best_match["id"]
        return None
    except Exception as e:
        print(f"Error connecting to Search API: {e}")
        return None


def get_related_tags(entity_id):
    """Get related tags from Wikidata using SPARQL"""
    sparql_query = f"""
    SELECT DISTINCT ?itemLabel WHERE {{
      {{ wd:{entity_id} wdt:P279 ?item. }}
      UNION
      {{ ?item wdt:P279 wd:{entity_id}. }}
      UNION
      {{ ?item wdt:P366 wd:{entity_id}. }}
      UNION
      {{ wd:{entity_id} wdt:P3095 ?item. }}
      UNION
      {{ wd:{entity_id} wdt:P1056 ?item. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 20
    """
    params = {"query": sparql_query, "format": "json"}
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(SPARQL_API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        results = []
        for result in data["results"]["bindings"]:
            label = result["itemLabel"]["value"]
            if label.startswith('Q') and label[1:].isdigit(): continue
            if label.startswith('L') and '-' in label: continue
            if label.isdigit(): continue
            if len(label) <= 2: continue
            results.append(label)
        return results
    except Exception as e:
        print(f"Error: {e}")
        return []


def get_wikidata_suggestions(query):
    """Get Wikidata tag suggestions for a search query"""
    if not query or len(query.strip()) < 2:
        return []
    
    q_id = get_entity_id(query.strip())
    if q_id:
        return get_related_tags(q_id)
    return []

