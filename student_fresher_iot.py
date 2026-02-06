import pandas as pd
import qrcode
import os

# 1. Load the data
# Use 'generated_students_500.csv' or 'Students_Data_500.xlsx'
file_path = 'Students_Data_500.xlsx' 
df = pd.read_excel(file_path)

# 2. Create a folder to store the QR codes
output_dir = "Student_QR_Codes"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"Starting QR code generation for {len(df)} students...")

# 3. Generate QR codes in a loop
for index, row in df.iterrows():
    # Define what data goes inside the QR code
    # We will use the UUID as the unique data
    qr_data = f"Name: {row['NAME ']}\nID: {row['UUID']}\nBranch: {row['BRANCH']}"
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save the image using the UUID as the filename to keep it unique
    file_name = f"{row['UUID']}.png"
    img.save(os.path.join(output_dir, file_name))

print(f"Done! All QR codes are saved in the '{output_dir}' folder.")