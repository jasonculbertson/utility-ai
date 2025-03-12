import os
import requests
import json
import pprint

def ocr_space_file(filename, overlay=False, api_key='K86742198888957', language='eng'):
    """ OCR.space API request with local file.
    :param filename: Your file path & name.
    :param overlay: Is OCR.space overlay required in your response.
                    Defaults to False.
    :param api_key: OCR.space API key.
    :param language: Language code to be used in OCR.
                    Defaults to 'eng'.
    :return: Result in JSON format.
    """

    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    return r.json()

def main():
    # Use the file in bills_to_process folder
    file_path = 'bills_to_process/2035custbill12112024.pdf'
    if not os.path.exists(file_path):
        print(f"Could not find {file_path}")
        return
    
    print(f"Processing file: {file_path}")
    # Get OCR.space output
    ocr_result = ocr_space_file(file_path)
    
    # Save the raw JSON output to a file
    with open('ocr_space_raw_output.json', 'w') as f:
        json.dump(ocr_result, f, indent=4)
    print(f"Raw OCR.space output saved to ocr_space_raw_output.json")
    
    # Pretty print the output
    print("\nOCR.space API Response:")
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(ocr_result)

if __name__ == "__main__":
    main()
