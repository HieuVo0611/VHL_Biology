import originpro as op
import pandas as pd
import os
import time

# Đường dẫn file
file_path = r"e:\VHL Project\Bio Zone\VHL_Biology\data\GGA\File txt\N4-VS1-25-03-2024\5-0\N4-5-0-29032024-Q=50.19mL_phut_1_copy.txt"

if not os.path.exists(file_path):
    raise FileNotFoundError(f"Không tìm thấy file tại {file_path}")

# Đọc dữ liệu
try:
    data = pd.read_csv(file_path, sep='\t', header=None, names=['X', 'Y'], encoding='utf-8-sig')
except UnicodeDecodeError:
    print("Lỗi UTF-8-SIG. Thử UTF-16...")
    data = pd.read_csv(file_path, sep='\t', header=None, names=['X', 'Y'], encoding='utf-16')

print("Dữ liệu đầu (5 dòng):")
print(data.head())

op.set_show(True)
print("Origin mở, kiểm tra Script Window (Ctrl+Alt+S) để xem log.")

op.new()
wks = op.new_sheet('w', 'MyData')
wks.from_df(data)
graph = op.new_graph(template='line')
layer = graph[0]
layer.add_plot(wks, colx=0, coly=1)
layer.rescale()

# LabTalk script với ROI trượt và log chi tiết
lt_script = """
// Kích hoạt Script Window để hiển thị log
win -a SW;
// Bắt đầu quy trình
type -b "Quy trình bắt đầu.";
layer -s 0;
addtool_quickpeaks;  // Tạo ROI Box mặc định
gadget gg = rect;  // Tên object mặc định
if (!gg) {
    type -b "Error: Gadget rect not found! Thử quickpeaks hoặc kiểm tra Object Properties.";
} else {
    type -b "Gadget rect added thành công.";
    // Lấy phạm vi X của dữ liệu
    range r = 1!1;  // Cột X
    double xMin = r.xmin;
    double xMax = r.xmax;
    int nSteps = 10;  // Số bước trượt
    double stepSize = (xMax - xMin) / nSteps;
    tree trgui;
    gg.gettree(trgui);
    type -b "Gettree thực hiện thành công.";
    // Output Quantities
    trgui.output.datasetid = 1;  // Plot Legend
    trgui.output.quantities.peakid = 1; trgui.output.quantities.peakrow = 1;
    trgui.output.quantities.peakx = 1; trgui.output.quantities.peaky = 1;
    trgui.output.quantities.height = 1; trgui.output.quantities.area = 1;
    trgui.output.quantities.fwhm = 1; trgui.output.quantities.info = 1;
    trgui.output.quantities.centroid = 0;
    type -b "Output Quantities thiết lập xong.";
    // Baseline
    trgui.baseline.mode = 2;  // Min&Max
    trgui.baseline.range = 1;  // Curve Within ROI
    type -b "Baseline thiết lập xong.";
    // Find Peak
    trgui.find.direction = 1;  // Negative
    trgui.find.method = 0; trgui.find.localpoints = 5;
    trgui.find.filter.method = 1; trgui.find.filter.number = 1; trgui.find.filter.auto = 0;
    trgui.find.display.peakmarker = 1; trgui.find.display.peakmarkercolor = 3; trgui.find.display.peakmarkersize = 10;
    trgui.find.display.peaklabel = 1; trgui.find.display.peaklabellabel = 1; trgui.find.display.peaklabelhorizontal = 1; trgui.find.display.peaklabelcolor = 0;
    trgui.find.display.basemarker = 1; trgui.find.display.basemarkercolor = 1; trgui.find.display.basemarkersize = 10;
    trgui.find.display.tagas = 0;
    type -b "Find Peak thiết lập xong.";
    // Area
    trgui.area.integrate = 1; trgui.area.integrationfrom = 0; trgui.area.showintegratedarea = 1;
    type -b "Area thiết lập xong.";
    // Output worksheets
    trgui.output.resultwks$ = "[QkPeak]Result";
    trgui.output.tagwks$ = "[QkPeak]Tag";
    trgui.output.baselinewks$ = "[QkPeak]Baseline";
    gg.settree(trgui);
    type -b "Config áp dụng thành công.";
    // Trượt ROI qua toàn bộ dữ liệu
    for (int i = 0; i <= nSteps; i++) {
        double xPos = xMin + i * stepSize;
        gg.x = xPos;  // Di chuyển trung tâm ROI
        type -b "ROI di chuyển đến x = %{xPos}";
        gg.output(4);  // Output cho toàn bộ curve
        delay 1;  // Delay để đảm bảo output
    }
    type -b "Output hoàn tất cho tất cả vị trí. Kiểm tra [QkPeak]Result.";
}
"""

op.lt_exec(lt_script)

result_wks = op.find_sheet('w', '[QkPeak]Result')
peaks_data = {}
if result_wks:
    peaks_data['peak_id'] = result_wks.to_list(0)
    peaks_data['peak_row'] = result_wks.to_list(1)
    peaks_data['x_positions'] = result_wks.to_list(2)
    peaks_data['y_positions'] = result_wks.to_list(3)
    peaks_data['heights'] = result_wks.to_list(4)
    peaks_data['areas'] = result_wks.to_list(5)
    peaks_data['fwhm'] = result_wks.to_list(6)
else:
    print("Error: Không tìm thấy [QkPeak]Result")

print("Kiểm tra Origin: Script Window log, graph ROI, worksheets. Đóng thủ công.")
time.sleep(60)  # Delay 60 giây để kiểm tra

for key, value in peaks_data.items():
    print(f"{key}: {value}")