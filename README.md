# QR Code Generator

Turn images into QR codes in two ways:

- **Data mode**: `python qr_code_generator/qr_code_generator.py -i <image> -o out.png`
- **Brand mode**: `python qr_code_generator/qr_code_generator.py -i <text_or_url> -l <logo_image> -o out.png`

Or use the upload UI:

```bash
python app.py
```

Then open `http://127.0.0.1:7860/` and upload any `jpg`, `png`, or `webp` picture.

## Outputs

Data QR: `samples/CCRA_Logo_data_qr.png`  
Branded QR: `samples/CCRA_Logo_branded_qr.png`
