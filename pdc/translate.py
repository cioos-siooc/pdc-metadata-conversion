import os
import boto3
import hashlib
import json
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


CACHE_FILE = os.getenv("TRANSLATION_CACHE","translation_cache.json")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESSKEYID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRETACCESSKEY")
TERMINOLOGY_CSV = os.getenv("TERMINOLOGY_CSV")


def get_translator():
    """Get the AWS Translate client."""
    if not AWS_REGION or not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        logger.error("AWS credentials are not set in environment variables.")
        raise ValueError("AWS credentials are not set in environment variables.")
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "w") as f:
            json.dump({}, f)
    return boto3.client(
        service_name="translate",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_cache_key(text, source_language, target_language):
    return hashlib.md5(
        f"{text}-{source_language}-{target_language}".encode()
    ).hexdigest()


cache = load_cache()


def translate(text, source_language, target_language, terminology_name=None):

    aws_translate = get_translator()

    cache = load_cache()
    cache_key = get_cache_key(text, source_language, target_language)
    if cache_key in cache:
        logger.debug("Use cached translation")
        return cache[cache_key]

    result = aws_translate.translate_text(
        Text=text,
        SourceLanguageCode=source_language,
        TargetLanguageCode=target_language,
        TerminologyNames=[terminology_name] if terminology_name else [],
    )

    translated_text = result.get("TranslatedText")
    cache[cache_key] = translated_text
    save_cache(cache)

    return translated_text

def get_french_translated_cioos_record(record):
    """Translate a CIOOS record to English using AWS Translate."""

    def _apply_french_transation(field):
        field['fr'] = translate(
            field['en'],
            source_language="en",
            target_language="fr",
            terminology_name=TERMINOLOGY_CSV,
        )
        field['translations'] ={
            "fr":  {
                "message": "text translated using the Amazon translate service / texte traduit à l'aide du service de traduction Amazon",
                "verified": False,
            }
        }
        return field

    logger.debug("Translating record: {}", record)
    record["title"] = _apply_french_transation(record["title"])
    record["abstract"] = _apply_french_transation(record["abstract"])
    record["limitations"] = _apply_french_transation(record.get("limitations"))
    record["comments"] = _apply_french_transation(record.get("comments"))

    for item in record.get('distributions', []):
        item['name'] = _apply_french_transation(item['name'])
        item['description'] = _apply_french_transation(item['description'])

    for item in record.get('associated_ressources', []):
        item['title'] = _apply_french_transation(item['title'])
        item['description'] = _apply_french_transation(item['description'])
    
    return record