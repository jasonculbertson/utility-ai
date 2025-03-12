# PG&E Bill Processor

A web application that processes PG&E bills, extracts key information, and provides rate plan analysis. The application supports both PDF bill uploads and manual data entry.

## Features

- **PDF Bill Upload**: Upload and process PG&E bills in PDF format
- **Manual Data Entry**: Manually enter bill information through a user-friendly form
- **Auto-Populate Rates**: Automatically fills in peak and off-peak rates based on the selected rate plan
- **Rate Plan Analysis**: Analyzes your usage to suggest the most cost-effective rate plan
- **Bill History**: View and compare all processed bills

## Rate Plans

The application supports various PG&E rate plans including:

- E-1: Flat Rate (Tiered Pricing)
- E-TOU-B: Time-of-Use (4-9pm Peak)
- E-TOU-C: Time-of-Use (4-9pm Peak)
- E-TOU-D: Time-of-Use (3-8pm Peak)
- EV2-A: Time-of-Use (EV Owners)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/jasonculbertson/utilityai.git
   cd utilityai
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python -c "import simple_bill_processor; simple_bill_processor.app.run(host='0.0.0.0', port=8095, debug=True)"
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:8095
   ```

## Environment Variables

Create a `.env` file with the following variables (if using OpenAI for PDF processing):

```
OPENAI_API_KEY=your_openai_api_key
```

## License

MIT
