import os
import pandas as pd
import glob

# Initialize an empty DataFrame to store data from all files
all_data = pd.DataFrame()
# read_files = []

def process_file_without_bom(file):
    # Initialize empty lists for Time and DO columns
    Time_list = []
    DO_list = []

    # Open file to read
    with open(file, "r") as f:
        # Read each line in the file
        for line in f:
            # Split the line into values based on space
            parts = line.split()
            if len(parts) < 2:
                continue
            # Add values to the corresponding lists
            Time_list.append(float(parts[0].replace("\x00","")))
            DO_list.append(float(parts[1].replace("\x00","")))

    # Create a dictionary from the lists
    temp_dict = {"Time": Time_list, "DO": DO_list}
    # Convert the dictionary to a DataFrame
    temp_data = pd.DataFrame(temp_dict)
    return temp_data

# Iterate over all txt files in the directory and subdirectories
for file in glob.glob("BOD2024-Nhung/GGA-metal/File txt/**/*.txt", recursive=True):
    print(f"Reading file: {file}")
    try:
        # Attempt to read file with UTF-16 encoding
        temp_data = pd.read_csv(file, sep="\t", header=None, names=["Time", "DO"], encoding='utf-16')
    except UnicodeError as e:
        if "UTF-16 stream does not start with BOM" in str(e):
            # Process the file without BOM if UTF-16 fails
            temp_data = process_file_without_bom(file)
        else:
            print(f"Error reading {file} with UTF-16: {e}")
            continue

    # Add the file name as a new column 'Sample_name'
    temp_data["Sample_name"] = os.path.basename(file).strip()
    
    # Append the data to the all_data DataFrame
    all_data = pd.concat([all_data, temp_data])
    # read_files.append(file)

# To check all actual files in the directory
# all_files = glob.glob("BOD2024-Nhung/GGA/File txt/**/*.txt", recursive=True)

# Compare the list of read files with the list of actual files
# missing_files = set(all_files) - set(read_files)
# if not missing_files:
#     print("All files have been read and processed.")
# else:
#     print("The following files were not read:")
#     for file in missing_files:
#         print(file)

# Reset the index of the final DataFrame
all_data.reset_index(drop=True, inplace=True)

# Check for rows with missing values
# missing_values = all_data[all_data.isna().any(axis=1)]
# if not missing_values.empty:
#     print("The following rows have missing values:")
#     print(missing_values)

# Display the DataFrame containing all the data
# print(all_data.head())

all_data.to_csv("metadata-gga_metal-txt.csv", index=False, encoding="utf-8-sig")