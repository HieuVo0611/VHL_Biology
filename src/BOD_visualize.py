import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
import seaborn as sns

file_name = "./biology/metadata-gga.csv"
raw_data = pd.read_csv(file_name)
df = raw_data.iloc[:,1:]
df.head()

def plot_sample_data(sample_name, df, ax):
    sample_data = df[df['Tên mẫu'] == sample_name]
    types = sample_data['Loại'].unique()  # Get unique types within the sample
    
    ax.clear()  # Clear the current axes before drawing a new plot

    for t in types:
        type_data = sample_data[sample_data['Loại'] == t]
        # Plot each line with unique label
        sns.lineplot(data=type_data, x='No.peak', y='Doin (mV)', ax=ax, label=f'{t} - Doin', linestyle='-', marker='o')
        sns.lineplot(data=type_data, x='No.peak', y='DOmin (mV)', ax=ax, label=f'{t} - DOmin', linestyle='--', marker='x')
        sns.lineplot(data=type_data, x='No.peak', y='DDO (mV)', ax=ax, label=f'{t} - DDO', linestyle='-.', marker='s')

    ax.set_title(f'{sample_name}')
    ax.set_xlabel('No.peak')
    ax.set_ylabel('Values (mV)')
    ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1))
    ax.grid(True)
    plt.tight_layout()
    plt.draw()

# Extract unique sample names
sample_names = df['Tên mẫu'].unique()

# Initial plot setup
fig, ax = plt.subplots(figsize=(10, 6))
plt.subplots_adjust(bottom=0.25)  # Adjust space for the slider

# Plot the first sample initially
plot_sample_data(sample_names[0], df, ax)

# Create the slider axis and the slider itself
ax_slider = plt.axes([0.2, 0, 0.65, 0.03], facecolor='lightgoldenrodyellow')
slider = Slider(ax_slider, 'Sample', 0, len(sample_names) - 1, valinit=0, valstep=1)

# Update plot when the slider is changed
def update(val):
    sample_index = int(slider.val)
    plot_sample_data(sample_names[sample_index], df, ax)

slider.on_changed(update)

plt.show()