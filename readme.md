# Financial Document Processor

A Python-based automation pipeline for extracting, processing, and analyzing financial transactions from various document formats stored in a folder in Google Drive. This tool streamlines the process of converting financial documents (PDFs, images, Word docs) into structured CSV data to limit the manual work.

## Overview

This system provides an end-to-end solution for financial document processing:

1. **Download** documents from Google Drive folders by providing the link
2. **Extract** text from PDFs, images, and Word documents using OCR
3. **Process** extracted text using Google's Gemini AI to identify financial transactions
4. **Export** structured data to CSV format

## Features

- **Multi-format support**: PDF, DOCX, DOC, JPG, PNG, TIFF, BMP
- **OCR text extraction** from images and scanned documents
- **AI-powered transaction detection** using Google Gemini
- **Configurable data schema** for different transaction types
- **Batch processing** that limits the number of request sent to AI to accommodate free plans limits
- **Visual snapshots** generation for document verification when needed
- **Automatic CSV export** with customizable fields

## Prerequisites

### System Requirements

**Windows Users:**

- Python 3.7 or higher
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- [Poppler for Windows](https://blog.alivate.com.au/poppler-windows/)

**macOS Users:**

```bash
# Install via Homebrew
brew install tesseract poppler
```

**Linux Users:**

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils

# CentOS/RHEL
sudo yum install tesseract poppler-utilsth
```

### API Requirements

1. **Google Drive API**: For downloading documents
2. **Google Gemini API**: For AI-powered transaction extraction

## Installation

1. **Clone the repository:**

```bash
git clone <repository-url>
cd financial-document-processor
```

2. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up Google Drive API:**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Drive API
   - Create OAuth 2.0 credentials (Desktop Application)
   - Download `credentials.json` and place in project root

4. **Set up Google Gemini API:**
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Generate an API key
   - Update `config.ini` with your API key

## Configuration

Edit `config.ini` to customize the processing behavior:

```ini
[Settings]
combination_count = 3  # Number of files to combine per text file to limit the batches sent to the api count

[Gemini]
api_key = YOUR_GEMINI_API_KEY_HERE
model_name = models/gemini-1.5-flash-latest
max_retries = 5
initial_delay = 1

[GeminiSchema]
# Define the structure of data to extract
response_schema = {
  "type": "ARRAY",
  "items": {
    "type": "OBJECT",
    "properties": {
      "original_file_name": {"type": "STRING"},
      "date": {"type": "STRING", "description": "Transaction date in YYYY-MM-DD format"},
      "vendor_name": {"type": "STRING"},
      "amount": {"type": "NUMBER"},
      "currency": {"type": "STRING"}
    },
    "required": ["original_file_name", "date", "vendor_name", "amount", "currency"]
  }
}

[Prompts]
financial_extraction_prompt =
    Analyze the following financial document text.
    Identify all distinct financial transactions. For each transaction, extract: {fields}
    Return as JSON array. If no transactions found, return empty array [].

    Document text:
    {content}
```

## Usage

### Step 1: Download Documents from Google Drive

```bash
python driver_downloader.py
```

- Enter your Google Drive folder ID or full URL when prompted
- Files will be downloaded to a timestamped folder
- Metadata file (`files_metadata.json`) is automatically generated

### Step 2: Extract Text from Documents

```bash
python files_extractor.py
```

- Provide the path to your downloaded folder
- The script generates:
  - `Extracted Texts with Snapshots_[folder].docx` - Visual report with document snapshots
  - `Extracted Texts_[folder].docx` - Combined text extraction
  - `Extracted Texts for Iteration_[folder]/` - Individual text files for processing
    x

### Step 3: Process with AI

```bash
python ai_processor.py
```

- Provide paths to:
  - Extracted texts folder (from Step 2)
  - Original timestamped folder (from Step 1)
- The script uses Gemini AI to extract structured transaction data
- Output: `financial_extracted_data.json`

### Step 4: Export to CSV

```bash
python output_to_csv.py
```

- Converts JSON data to CSV format
- Output: `financial_report.csv`
- Column headers are automatically generated from your schema configuration

## Output Files

### Primary Outputs

- `financial_report.csv` - Final structured data ready for analysis
- `financial_extracted_data.json` - Raw AI extraction results

### Intermediate Files

- `Extracted Texts with Snapshots_[folder].docx` - Visual verification document
- `Extracted Texts_[folder].docx` - Combined text extraction
- `Extracted Texts for Iteration_[folder]/` - Processed text files

## Customization

### Adding New Document Types

Extend the `get_file_text()` function in `files_extractor.py`:

```python
def get_file_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.your_format':
        return extract_text_from_your_format(file_path)
    # ... existing code
```

### Modifying Data Schema

Update the `response_schema` in `config.ini` to change extracted fields:

```json
{
  "type": "ARRAY",
  "items": {
    "type": "OBJECT",
    "properties": {
      "your_field": { "type": "STRING", "description": "Field description" }
      // ... other fields
    }
  }
}
```

### Custom AI Prompts

Modify the `financial_extraction_prompt` in `config.ini` to adjust AI behavior for different document types or extraction requirements.

## Error Handling

The system includes comprehensive error handling:

- **Retry logic** for API failures with exponential backoff
- **Format validation** for extracted data
- **Missing file detection** and reporting
- **OCR fallback** for problematic documents

Common issues and solutions:

| Issue                 | Solution                              |
| --------------------- | ------------------------------------- |
| Tesseract not found   | Install Tesseract OCR and add to PATH |
| PDF processing fails  | Install Poppler utilities             |
| API quota exceeded    | Check Gemini API usage limits         |
| Authentication errors | Regenerate `credentials.json`         |

## Performance Considerations

- **Batch processing**: Files are processed in configurable batches to accommodate the API requests quota
- **Rate limiting**: Built-in delays prevent API quota issues
