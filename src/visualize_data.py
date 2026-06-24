import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Read DATA "DATA TXT GỐC" and "DATA EXCEL GỐC"
file_name = "data/GGA/File txt/N4-VS1-25-03-2024/15-10/N4-15-10-27032024-Q=49.66mL_phút-1.txt"
raw_data = pd.read_csv(file_name, header=None, names=["Time", "DO"], encoding="utf-16")
time_list = []
do_list = []
for i in range(len(raw_data)):
    time_raw = raw_data["Time"][i]
    time_list.append(int(time_raw.split("\t")[0]))
    do_list.append(float(time_raw.split("\t")[1]))
data_dict = {"Time": time_list, "DO": do_list}
data_txt = pd.DataFrame(data_dict)
data_excel = pd.read_csv("data/metadata-gga-2024-10-23.csv")

def get_sheet_and_sample_name(file_name):
    sheet_name_split = file_name.split("/")
    txt_sheet_name = sheet_name_split[3].replace("-VS1","").replace("-"," ")

    sample_name_split = file_name.split("/")[5].split("-",4)
    txt_sample_name = "-".join([sample_name_split[3], "BOD", sample_name_split[1], sample_name_split[2], sample_name_split[4].replace("_","/")])

    return txt_sheet_name, txt_sample_name.replace(".txt","")

# Function to find the approximate value within a given threshold
def tim_gia_tri_gan_dung(value, threshold=0.1):
    return data_txt[(np.abs(data_txt["DO"] - value) <= threshold)]

# Find the peak points
peaks = []

# Find special times and their approximate rounded values
txt_sheet_name, txt_sample_name = get_sheet_and_sample_name(file_name)
result = []
temp_BOD = ""
BOD_type_list = []
change = 0
data_part_1 = []
data_part_2 = []
time_change = 0

for i, row in data_excel.iterrows():
    sheet_name = row["Sheet Name"].replace("-"," ").replace("."," ")
    sample_name = row["Sample Name"]
    if (
        sheet_name == txt_sheet_name
        and 
        sample_name == txt_sample_name
    ):
        # If row[]
        peak_time = row["No.peak"]
        do_in = row["Doin (mV)"]
        do_min = row["DOmin (mV)"]
        
        # If the type changes
        if (temp_BOD != row["Tag"]):
            if temp_BOD != "": 
                temp_BOD = row["Tag"]
                change = 1
            temp_BOD = row["Tag"]
            BOD_type_list.append(row["Tag"])

        if change == 1:
            if time_change == 0: 
                time_change = row["No.peak"]

        # Find the index of the special time in data_txt
        index = data_txt[data_txt["Time"] == peak_time].index[0]

        # Store the Peak value
        peaks.append((int(peak_time), float(do_min)))

        # Find backwards and find the approximate rounded value
        for j in range(index, -1, -1):
            if abs(data_txt.at[j, "DO"] - do_in) <= 0.01:
                result.append((data_txt.at[j, "Time"], data_txt.at[j, "DO"]))
                break

# Find Doin Point and Peak Point
doin_value_list = []
doin_time_list = []
peak_time_list = []
peak_value_list = []

for doin_point in result:
    doin_time_list.append(doin_point[0])
    doin_value_list.append(doin_point[1])

for peak_point in peaks:
    peak_time_list.append(peak_point[0])
    peak_value_list.append(peak_point[1])

# Plot the figures
plt.figure(figsize=(12, 6))

# Split data into 2 parts
part_1 = data_txt[data_txt['Time'] <= time_change]
part_2 = data_txt[data_txt['Time'] > time_change]

# Plot part 1 of graph
plt.plot(part_1['Time'], part_1['DO'], color='blue', label=BOD_type_list[0])

# Plot part 1 of graph
plt.plot(part_2['Time'], part_2['DO'], color='purple', label=BOD_type_list[1])

plt.xlabel("Time")
plt.ylabel("DO")
plt.title(txt_sample_name)
plt.grid(True)
plt.scatter(doin_time_list, doin_value_list, color='red', label='DOIN')
plt.scatter(peak_time_list, peak_value_list, color='green', label='PEAK')

# Add legend
plt.legend()

# Save figure
plt.savefig('doin_peak.png')
