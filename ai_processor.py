import os
import json
import time
import re
import requests
import sys
import configparser

PROCESSED_DATA_OUTPUT_FILE = "financial_extracted_data.json"

def call_gemini_api_with_retries(prompt_content, api_url, max_retries, initial_delay, response_schema):
    """
    Calls the Gemini API with a dynamic schema and exponential backoff.
    """
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_content}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": response_schema  # Use the schema from config
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(api_url, headers={'Content-Type': 'application/json'}, json=payload)
            response.raise_for_status()
            result = response.json()

            if result.get("candidates") and result["candidates"][0].get("content"):
                json_string = result["candidates"][0]["content"]["parts"][0]["text"]
                try:
                    return json.loads(json_string)
                except json.JSONDecodeError:
                    match = re.search(r'\[.*\]|\{.*\}', json_string, re.DOTALL)
                    if match:
                        try:
                            return json.loads(match.group(0))
                        except json.JSONDecodeError as e:
                            print(f"Attempt {attempt + 1}: Could not parse JSON from response substring: {e}")
                    else:
                        print(f"Attempt {attempt + 1}: No JSON found in response: {json_string}")
            else:
                 print(f"Attempt {attempt + 1}: Gemini API returned unexpected structure: {result}")

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1}: Request failed: {e}")
        except Exception as e:
            print(f"Attempt {attempt + 1}: An unexpected error occurred: {e}")

        if attempt < max_retries - 1:
            delay = initial_delay * (2 ** attempt)
            print(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
        else:
            print("Max retries reached. Failed to get a valid response from Gemini API.")
    return None

def load_metadata(target_folder_path):
    """Loads the files_metadata.json to map filenames to Google Drive links."""
    metadata_path = os.path.join(target_folder_path, 'files_metadata.json')
    if not os.path.exists(metadata_path):
        return {}
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return {
            file_info.get('filename'): file_info.get('link', 'Link not available')
            for file_info in metadata.values() if file_info.get('filename')
        }
    except Exception as e:
        print(f"Error loading metadata: {e}")
        return {}

def process_combined_text_file(file_path, filename_to_link_mapping, api_url, max_retries, initial_delay, prompt_template, response_schema):
    """
    Reads a text file, builds a prompt from the config template, and extracts data.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Dynamically create the list of fields from the schema for the prompt
        fields_for_prompt = ", ".join(response_schema.get("items", {}).get("properties", {}).keys())
        
        # Format the prompt with the fields and the file content
        prompt_for_gemini = prompt_template.format(fields=fields_for_prompt, content=content)

        gemini_response = call_gemini_api_with_retries(prompt_for_gemini, api_url, max_retries, initial_delay, response_schema)

        if not gemini_response:
            print(f"No data extracted by Gemini for {os.path.basename(file_path)}")
            return []

        # Dynamically process the fields defined in the schema
        extracted_data = []
        defined_fields = list(response_schema.get("items", {}).get("properties", {}).keys())
        
        for transaction in gemini_response:
            processed_transaction = {}
            for field in defined_fields:
                processed_transaction[field] = transaction.get(field, "N/A")
            
            # Add the drive link separately
            original_name = transaction.get('original_file_name')
            processed_transaction['drive_link'] = filename_to_link_mapping.get(original_name, 'Link not found')
            extracted_data.append(processed_transaction)
            
        return extracted_data

    except Exception as e:
        print(f"Error processing combined file {file_path}: {e}")
        return []

def main():
    """Main execution function to read config, get user input, and process files."""
    config = configparser.ConfigParser()
    config.read('config.ini')

    # 1. Load settings from config.ini
    try:
        # Gemini API settings
        api_key = config.get('Gemini', 'api_key').strip().strip('"\'')
        model_name = config.get('Gemini', 'model_name')
        max_retries = config.getint('Gemini', 'max_retries')
        initial_delay = config.getint('Gemini', 'initial_delay')

        # Gemini schema and prompt settings
        schema_string = config.get('GeminiSchema', 'response_schema')
        response_schema = json.loads(schema_string) # Parse the JSON string into a dictionary
        prompt_template = config.get('Prompts', 'financial_extraction_prompt')

    except (configparser.Error, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading configuration from config.ini. Please check the file. Details: {e}")
        sys.exit(1)

    if not api_key or 'YOUR_GEMINI_API_KEY' in api_key:
        print("Error: Gemini API key is missing from config.ini.")
        sys.exit(1)
        
    api_url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"

    # 2. Get folder paths from user
    print("Please provide the paths to the required folders.")
    raw_texts_folder = input("Enter the path to the 'Extracted Texts for Iteration' folder: ").strip()
    source_folder = input("Enter the path to the original timestamped folder (containing metadata): ").strip()

    if not os.path.isdir(raw_texts_folder) or not os.path.isdir(source_folder):
        print("Error: One or both of the provided paths are not valid directories.")
        sys.exit(1)

    # 3. Process files
    filename_to_link_mapping = load_metadata(source_folder)
    print(f"\nLoaded metadata for {len(filename_to_link_mapping)} files.")
    
    all_processed_data = []
    text_files = [f for f in os.listdir(raw_texts_folder) if f.endswith('.txt')]

    for filename in text_files:
        file_path = os.path.join(raw_texts_folder, filename)
        print(f"\n--- Processing file: {filename} ---")
        
        processed_data = process_combined_text_file(
            file_path, filename_to_link_mapping, api_url, max_retries, initial_delay, prompt_template, response_schema
        )
        all_processed_data.extend(processed_data)
        time.sleep(1)

    # 4. Save results
    with open(PROCESSED_DATA_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_processed_data, f, indent=4)
    print(f"\nExtraction complete. All data saved to: {PROCESSED_DATA_OUTPUT_FILE}")
    print(f"Total transactions extracted: {len(all_processed_data)}")

if __name__ == '__main__':
    main()