import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from icecream import ic
from scipy.signal import savgol_filter
import os

MEAN_DECREASING_MAGNITUDE = 1.0
TREND_CHANGE_DISTANCE = 10
MEAN_TIME_DIFF_THRESHOLD = 30

# Load the data
# metadata = pd.read_csv('metadata-gga_metal-txt.csv')
metadata = pd.read_csv('metadata-gga-txt.csv')
sample_names_list = metadata["Sample_name"].unique()

# Thư mục lưu trữ biểu đồ
output_folder = f"plot_gga_{MEAN_DECREASING_MAGNITUDE}_{TREND_CHANGE_DISTANCE}/"
os.makedirs(output_folder, exist_ok=True)

def find_max_points(data, do_min_points_df):
    max_points = []

    for i in range(len(do_min_points_df) - 1):
        start_time = do_min_points_df.iloc[i]['Time']
        next_min_time = do_min_points_df.iloc[i + 1]['Time']

        section = data[(data['Time'] >= start_time) & (data['Time'] <= next_min_time)].copy()

        C_temp = None
        for j in range(len(section) - 2, -1, -1):
            is_valid_C_temp = True
            for k in range(j + 1, len(section)):
                if section.iloc[k]['DO'] >= section.iloc[j]['DO']:
                    is_valid_C_temp = False
                    break
            if is_valid_C_temp:
                C_temp = (section.iloc[j]['Time'], section.iloc[j]['DO'])
                break

        if C_temp is not None:
            for j in range(len(section) - 2, -1, -1):
                is_valid_C = True
                for k in range(j + 1, len(section)):
                    if section.iloc[k]['DO'] >= section.iloc[j]['DO']:
                        is_valid_C = False
                        break
                if is_valid_C:
                    C_temp = (section.iloc[j]['Time'], section.iloc[j]['DO'])
                else:
                    break

            max_points.append(C_temp)

    max_points_df = pd.DataFrame(max_points, columns=['Time', 'DO'])
    return max_points_df

def find_purple_points(data, do_min_points_df, max_points_df):
    max_points = []

    for i in range(len(do_min_points_df) - 1):
        start_time = do_min_points_df.iloc[i]['Time']
        next_min_time = do_min_points_df.iloc[i + 1]['Time']
        if max_points_df.iloc[i]["Time"] > start_time and max_points_df.iloc[i]["Time"] < next_min_time:
            section = data[(data['Time'] >= start_time) & (data['Time'] <= max_points_df.iloc[i]["Time"])].copy()
        else:
            section = data[(data['Time'] >= start_time) & (data['Time'] <= max_points_df.iloc[i+1]["Time"])].copy()

        C_temp = None
        WINDOW = 85
        STRIDE = 2
        # IF gradually decrease
        C_temp = None
        for j in range(len(section) - WINDOW, -1, -STRIDE):
            is_valid_C_temp = True
            for k in range(j + 1, len(section)):
                if section.iloc[k]['DO'] <= section.iloc[j]['DO']:
                    is_valid_C_temp = False
                    break
            if is_valid_C_temp:
                C_temp = (section.iloc[j]['Time'], section.iloc[j]['DO'])
                break
        if C_temp is not None:
            max_points.append(C_temp)

    max_points_df = pd.DataFrame(max_points, columns=['Time', 'DO'])
    return max_points_df

def find_min_points(time, values):
    # Smooth the data using a Savitzky-Golay filter
    smoothed_values = savgol_filter(values, window_length=51, polyorder=9)
    smoothed_series = pd.Series(smoothed_values, index=time)

    # Detect trends
    gradient = np.gradient(smoothed_values)
    trend_changes = np.where(np.diff(np.sign(gradient)) != 0)[0] + 1
    trend_changes = np.insert(trend_changes, 0, 0)
    trend_changes = np.append(trend_changes, len(time) - 1)

    # Separate increasing and decreasing trends
    increasing_trends = []
    decreasing_trends = []

    for i in range(len(trend_changes) - 1):
        start_idx = trend_changes[i]
        end_idx = trend_changes[i + 1]
        segment_time = time.iloc[start_idx:end_idx].values
        segment_values = smoothed_values[start_idx:end_idx]
        if gradient[start_idx] > 0:
            increasing_trends.append((segment_time, segment_values))
        else:
            decreasing_trends.append((segment_time, segment_values))

    # Ensure all trends are valid before calculating magnitudes
    valid_increasing_trends = [seg for seg in increasing_trends if len(seg[1]) > 0]
    valid_decreasing_trends = [seg for seg in decreasing_trends if len(seg[1]) > 0]

    # Calculate the average magnitude based on valid trends
    average_magnitude = np.mean([
        abs(seg[1][-1] - seg[1][0]) for seg in valid_increasing_trends + valid_decreasing_trends
    ])

    # Filter trends with magnitude larger than the average
    magnitude_large_increasing_trends = [
        seg for seg in valid_increasing_trends if abs(seg[1][-1] - seg[1][0]) > average_magnitude
    ]
    magnitude_large_decreasing_trends = [
        seg for seg in valid_decreasing_trends if abs(seg[1][-1] - seg[1][0]) > average_magnitude
    ]

    # Calculate the mean magnitude of decreasing trends
    value_list = []
    for seg in magnitude_large_decreasing_trends:
        seg_height_peak = abs(seg[1][-1] - seg[1][0])
        value_list.append(seg_height_peak)

    intersection_points = []

    for dec_seg in magnitude_large_decreasing_trends:
        dec_end_time = dec_seg[0][-1]
        if abs(dec_seg[1][-1] - dec_seg[1][0]) >= MEAN_DECREASING_MAGNITUDE:
            for inc_seg in magnitude_large_increasing_trends:
                inc_start_time = inc_seg[0][0]
                if abs(dec_end_time - inc_start_time) <= TREND_CHANGE_DISTANCE:
                    intersection_value = smoothed_series.loc[dec_end_time]
                    intersection_points.append((dec_end_time, intersection_value))

    filtered_intersection_points = []

    for time_point, value in intersection_points:
        idx = time[time == time_point].index[0]  # Find index in the original data
        if 1 <= idx < len(smoothed_values) - 1:  # Ensure valid index range
            prev_value = smoothed_values[idx - 1]
            next_value = smoothed_values[idx + 1]
            local_max = max(prev_value, next_value)
            local_min = min(prev_value, next_value)
            if not (value > (2 * local_max) or value < (0.5 * local_min)):
                filtered_intersection_points.append((time_point, value))

    filtered_intersection_points_df = pd.DataFrame(
        filtered_intersection_points, columns=['Time', 'DO']
    )

    # Initialize the time difference list
    time_diff_list = []
    drop_indices = set()

    # Iterate through the filtered intersection points
    for i in range(len(filtered_intersection_points_df) - 1):
        time_diff_temp = filtered_intersection_points_df.iloc[i + 1]['Time'] - filtered_intersection_points_df.iloc[i]['Time']
        # ic(time_diff_temp, i)
        if i == 0:
            time_diff_list.append(time_diff_temp)
        else:
            mean_time_diff = np.mean(time_diff_list)
            # ic(mean_time_diff)
            if mean_time_diff - MEAN_TIME_DIFF_THRESHOLD <= time_diff_temp <= mean_time_diff + MEAN_TIME_DIFF_THRESHOLD:
                time_diff_list.append(time_diff_temp)
            else:
                # Check the next point to give a second chance
                if i + 2 < len(filtered_intersection_points_df):
                    next_time_diff_temp = filtered_intersection_points_df.iloc[i + 2]['Time'] - filtered_intersection_points_df.iloc[i]['Time']
                    if mean_time_diff - 30 <= next_time_diff_temp <= mean_time_diff + 30:
                        drop_indices.add(filtered_intersection_points_df.index[i + 1])
                        time_diff_list.append(next_time_diff_temp)
                    else:
                        drop_indices.add(filtered_intersection_points_df.index[i])
                else:
                    drop_indices.add(filtered_intersection_points_df.index[i])

    # Drop the indices after the loop
    # ic(filtered_intersection_points_df)
    # ic(drop_indices)
    filtered_intersection_points_df.drop(drop_indices, inplace=True)
    filtered_intersection_points_df.reset_index(drop=True, inplace=True)
    return smoothed_values, filtered_intersection_points_df

def extract_sections_between_do_min(data, do_min_points_df, do_max_points_df):
    sub_dfs = []

    # Lặp qua từng cặp điểm DO_min liền kề
    for i in range(len(do_min_points_df) - 1):
        start_time = do_min_points_df.iloc[i]['Time']
        next_min_time = do_min_points_df.iloc[i + 1]['Time']

        # Tìm điểm DO_max giữa start_time và next_min_time
        max_points_between = do_max_points_df[
            (do_max_points_df['Time'] > start_time) & 
            (do_max_points_df['Time'] < next_min_time)
        ]

        # Nếu có điểm DO_max, end_time sẽ là điểm DO_max đầu tiên
        if not max_points_between.empty:
            end_time = max_points_between.iloc[0]['Time'] -1 
        else:
            end_time = next_min_time

        # Trích các điểm giữa start_time và end_time từ dataframe gốc
        sub_df = data[(data['Time'] >= start_time) & (data['Time'] <= end_time)].copy()
        sub_df.reset_index(drop=True, inplace=True)
        
        # Thêm sub dataframe vào danh sách
        sub_dfs.append(sub_df)
    
    return sub_dfs

def calculate_angle(x1, y1, x2, y2):
    slope = (y2 - y1) / ((x2 - x1) + 0.0000000001)
    theta_radians = np.arctan(slope)
    theta_degrees = np.degrees(theta_radians)
    
    return theta_degrees

ic(len(sample_names_list))
count = 0
# plot_sample = "U1-10-5-03042024-Q=50.41mL_phút-5.txt"

# Vòng lặp qua tất cả các mẫu
for plot_sample in sample_names_list:
    ic(plot_sample)
    ic(count)
    data = metadata[metadata['Sample_name'] == plot_sample].copy()
    data.reset_index(drop=True, inplace=True)

    # Extract time and values
    time = data['Time']
    values = data['DO']

    # Find min points
    smoothed_values, do_min_points_df = find_min_points(time, values)
    smoothed_df = pd.DataFrame({
        "Time": data["Time"],
        "DO": smoothed_values,
    })

    # Find max points
    do_max_points_df = find_max_points(smoothed_df, do_min_points_df)
    # Find purple points (DO_in points)
    do_in_points_df = find_purple_points(smoothed_df, do_min_points_df, do_max_points_df)
    # Plot and save the figure
    plt.figure(figsize=(12, 6))
    plt.plot(time, smoothed_values, label='Smoothed Data', color='blue')

    if not do_max_points_df.empty:
        plt.scatter(do_max_points_df['Time'], do_max_points_df['DO'],
                    color='green', label='DO max (Start of Decrease Trend)', zorder=5)

    if not do_min_points_df.empty:
        plt.scatter(do_min_points_df['Time'], do_min_points_df['DO'],
                    color='red', label='DO min (Start of Increase Trend)', zorder=4)

    if not do_in_points_df.empty:
        plt.scatter(do_in_points_df['Time'], do_in_points_df['DO'],
                    color='purple', label='DO in', zorder=3)

    plt.title(plot_sample, fontsize=14)
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('DO', fontsize=12)
    plt.legend(['Smoothed Data', 'DO max (Start of Decrease Trend)', 'DO min (Start of Increase Trend)', "DO in"])
    plt.grid(True)
    # plt.show()

    # Save the figure to the specified folder
    plt.savefig(os.path.join(output_folder, f"{plot_sample}.png"))
    plt.close()
    count += 1

print(f"All plots saved to {output_folder}")
