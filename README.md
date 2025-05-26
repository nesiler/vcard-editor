# VCF Editor

A powerful desktop application for managing and editing VCF (vCard) contact files with support for iOS compatibility.

## Features

- Open and edit VCF contact files
- Save in standard or iOS-compatible format
- Export to CSV
- Advanced contact management features:
  - Remove duplicates (exact or fuzzy matching)
  - Normalize phone numbers
  - Title case names
  - Append codes to names
  - Make last word uppercase
  - Replace/delete text
  - Find matches from reference list
- Dark theme UI
- Multi-language support

## Requirements

- Python 3.8 or higher
- PyQt5
- pandas
- vobject
- fuzzywuzzy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/vcard-editor.git
cd vcard-editor
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python main.py
```

2. Basic Operations:
   - Open VCF: Load a VCF file
   - Save VCF: Save in standard format
   - Save VCF (iOS): Save in iOS-compatible format
   - Export CSV: Export contacts to CSV format

3. Data Editing:
   - Remove Duplicates: Find and remove duplicate contacts
   - Normalize Phone Numbers: Format phone numbers consistently
   - Title Case Names: Convert names to title case
   - Append Code: Add prefix or suffix to names
   - Make Last Word Upper: Convert last word to uppercase
   - Replace/Delete Text: Find and replace text in names
   - Delete Selected: Remove selected contacts
   - Find Matches: Find contacts matching a reference list

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PyQt5 for the GUI framework
- vobject for VCF file handling
- fuzzywuzzy for fuzzy string matching