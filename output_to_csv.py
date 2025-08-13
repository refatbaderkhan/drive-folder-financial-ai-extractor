import os
import json
import csv
import sys
import configparser

def transform_data_to_csv(input_json_file, output_csv_file):
    """
    Reads structured data from the input JSON file and writes it to a CSV file,
    with columns generated dynamically from the config.ini schema.
    """
    # --- Step 1: Check for the input JSON file ---
    if not os.path.exists(input_json_file):
        print(f"Error: Input file '{input_json_file}' not found.")
        print("Please ensure you have run ai_processor.py successfully first.")
        return False

    # --- Step 2: Load the AI's extracted data ---
    try:
        with open(input_json_file, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading '{input_json_file}': {e}")
        return False

    # --- Step 3: Dynamically generate headers from config.ini ---
    try:
        config = configparser.ConfigParser()
        config.read('config.ini')
        schema_string = config.get('GeminiSchema', 'response_schema')
        response_schema = json.loads(schema_string)
        
        # Get headers directly from the keys in the schema's "properties"
        headers = list(response_schema['items']['properties'].keys())
        
        # The 'drive_link' is added by the script, not the AI, so we add it manually.
        headers.append('drive_link')

    except (configparser.Error, json.JSONDecodeError, KeyError) as e:
        print(f"Error reading schema from config.ini to generate headers. Details: {e}")
        return False

    # --- Step 4: Write the data to the CSV file ---
    try:
        with open(output_csv_file, 'w', newline='', encoding='utf-8') as outfile:
            csv_writer = csv.writer(outfile)

            # Write the dynamically generated header row
            csv_writer.writerow(headers)

            # Loop through each transaction and write the data
            for item in extracted_data:
                # Create the row dynamically using the headers list
                # This ensures the data maps to the correct column automatically
                row = [item.get(header, "N/A") for header in headers]
                csv_writer.writerow(row)

        print(f"\nSuccessfully transformed data and created CSV file: {output_csv_file}")
        print(f"Columns were generated automatically: {', '.join(headers)}")
        return True
    except Exception as e:
        print(f"An error occurred while writing the CSV file: {e}")
        return False

def main():
    """Main function to run the transformation."""
    PROCESSED_DATA_INPUT_FILE = "financial_extracted_data.json"
    OUTPUT_CSV_FILE = "financial_report.csv"
    
    print(f"Attempting to transform '{PROCESSED_DATA_INPUT_FILE}' to '{OUTPUT_CSV_FILE}'")

    if transform_data_to_csv(PROCESSED_DATA_INPUT_FILE, OUTPUT_CSV_FILE):
        print("\n" + "="*80)
        print("CSV File Generated. Columns were created automatically based on your config.ini.")
        print("="*80)
    else:
        print("\nData transformation failed. Please check the errors listed above.")

if __name__ == '__main__':
    main()