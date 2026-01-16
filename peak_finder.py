import originpro as op
import pandas as pd
import os
import time

# Đường dẫn file
import sys

# Accept file path from CLI; fall back to example path
# Build file path from all CLI args so users don't need to quote paths with spaces.
if len(sys.argv) > 1:
    # join all args after script name into one string (handles unquoted paths with spaces)
    file_path = ' '.join(sys.argv[1:]).strip().strip('"').strip("'")
    # expand to absolute path
    file_path = os.path.abspath(os.path.expanduser(file_path))
else:
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

# Try to determine the graph window name to activate it in LabTalk
graph_name = None
try:
    # common attributes on Origin graph objects
    graph_name = getattr(graph, 'name', None) or getattr(graph, 'caption', None) or getattr(graph, 'title', None)
except Exception:
    graph_name = None
if not graph_name:
    # fallback common window name
    graph_name = 'Graph1'

# LabTalk script với ROI trượt và log chi tiết
# Prepend a small activation command using the detected graph name, then the raw LabTalk body
lt_script = 'win -a ' + graph_name + ';\n' + """
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
    int nSteps = 10;  // Số bước trượt (ROI)
    double stepSize = (xMax - xMin) / nSteps;
    tree trgui;
    gg.gettree(trgui);
    type -b "Gettree thực hiện thành công.";
    // Output Quantities (match Quick Peaks preferences)
    trgui.output.datasetid = 1;
    trgui.output.quantities.peakid = 1; trgui.output.quantities.peakrow = 1;
    trgui.output.quantities.peakx = 1; trgui.output.quantities.peaky = 1;
    trgui.output.quantities.height = 1; trgui.output.quantities.area = 1;
    trgui.output.quantities.fwhm = 1; trgui.output.quantities.info = 1;
    trgui.output.quantities.centroid = 0;
    type -b "Output Quantities thiết lập xong.";
    // Baseline: 2nd Derivative + Adjacent-Averaging smoothing
    trgui.baseline.mode = 2;  // 2nd Derivative
    trgui.baseline.range = 1;  // Curve Within ROI
    trgui.baseline.smoothing.method = 0; // Adjacent-Averaging (heuristic)
    trgui.baseline.smoothing.window = 1; // Window Size = 1
    trgui.baseline.threshold = 0.05; // Threshold from screenshot
    trgui.baseline.maxanchorpoints = 8;
    type -b "Baseline thiết lập xong.";
    // Find Peak: Local Maximum, Local Points = 5
    trgui.find.method = 0; // Local Maximum
    trgui.find.localpoints = 5;
    // Peak Filtering: By Height, Threshold Height(%) = 10
    trgui.find.filter.method = 1; // By Height (heuristic mapping)
    trgui.find.filter.heightpercent = 10;
    trgui.find.filter.auto = 0;
    // Peak display options
    trgui.find.display.peakmarker = 1; trgui.find.display.peakmarkercolor = 3; trgui.find.display.peakmarkersize = 10;
    trgui.find.display.peaklabel = 1; trgui.find.display.peaklabellabel = 1; trgui.find.display.peaklabelhorizontal = 1; trgui.find.display.peaklabelcolor = 0;
    trgui.find.display.basemarker = 1; trgui.find.display.basemarkercolor = 1; trgui.find.display.basemarkersize = 10;
    trgui.find.display.tagas = 0;
    type -b "Find Peak thiết lập xong.";
    // Area: integrate individual peaks using baseline
    trgui.area.integrate = 1; trgui.area.integrationfrom = 0; trgui.area.showintegratedarea = 1;
    type -b "Area thiết lập xong.";
    // Output worksheets
    trgui.output.resultwks$ = "[QkPeak]Result";
    trgui.output.tagwks$ = "[QkPeak]Tag";
    trgui.output.baselinewks$ = "[QkPeak]Baseline";
    gg.settree(trgui);
    type -b "Config áp dụng thành công.";
    // Trượt ROI qua toàn bộ dữ liệu (user can move ROI interactively; script slides by default)
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

# Execute LabTalk script in Origin
print('Running Quick Peaks LabTalk script in Origin...')
script_path = os.path.join('data', 'quickpeaks_script.lt')
os.makedirs('data', exist_ok=True)
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(lt_script)
print(f'Wrote LabTalk script to {script_path} (you can paste it into Origin Script Window).')

# Snapshot existing worksheet names
def list_workbook_sheets():
    try:
        wks_list = [s.name for s in op.find_sheet('w')]
    except Exception:
        # op.find_sheet('w') may return None or raise; fallback to empty
        try:
            wks_objs = op.find_sheet('w')
            if not wks_objs:
                return []
            return [w.name for w in wks_objs]
        except Exception:
            return []

before_sheets = list_workbook_sheets()
print('Worksheets before:', before_sheets)

# Quick sanity test: run a tiny LabTalk snippet to check Origin <-> Python link
test_lt = 'type -b "[Python->LabTalk] quick test";'
try:
    test_ret = op.lt_exec(test_lt)
    print('Quick LabTalk test returned:', repr(test_ret))
    if test_ret is False:
        print('Origin did not accept the quick LabTalk snippet via op.lt_exec.')
        print('Possible causes: Origin not running, COM API not enabled, or Origin security settings block scripts.')
        print('Please open Origin, then open Script Window (Ctrl+Alt+S), open the file', script_path)
        print('and run it manually to see Script Window log messages.')
    else:
        # Run the main Quick Peaks script only if the test succeeded
        # Additional test: try adding the Quick Peaks gadget via LabTalk to verify gadget availability
        try:
            addtool_test = 'addtool_quickpeaks; type -b "addtool_quickpeaks returned";'
            addtool_ret = op.lt_exec(addtool_test)
            print('addtool_quickpeaks test returned:', repr(addtool_ret))
            if addtool_ret is False:
                print('addtool_quickpeaks failed via op.lt_exec. Run the saved script manually in Origin Script Window.')
            else:
                try:
                    # Probe for gadget object name by testing common candidates one-by-one
                    candidates = [
                        'rect', 'rect1', 'rect2', 'Rect1', 'Rect', 'QuickPeaks', 'quickpeaks', 'QkPeak', 'QkPeaks', 'QuickPeak'
                    ]
                    print('Probing gadget name candidates via op.lt_exec...')
                    found_name = None
                    for nm in candidates:
                        cmd = f'gadget gg = {nm}; if(gg) type -b "FOUND: {nm}"; else type -b "NOTFOUND: {nm}";'
                        r = op.lt_exec(cmd)
                        print('Probe', nm, 'returned:', repr(r))
                        # Some versions return True/False; also check Script Window if you run manually
                        if r not in (False, None):
                            # assume success if not False/None — record candidate and break
                            found_name = nm
                            break
                    if found_name:
                        print('Likely gadget name:', found_name)
                    else:
                        print('No gadget candidate returned True via op.lt_exec; please run the small probe commands manually in Origin Script Window or inspect Object Manager.')

                    # Run the large script in smaller, logged steps so we can detect which part fails
                    steps = [
                        "type -b \"Running Quick Peaks step: addtool_quickpeaks\"; addtool_quickpeaks; type -b \"addtool_quickpeaks done\";",
                        "type -b \"Running Quick Peaks step: gadget assign\"; gadget gg = rect; if(!gg) type -b \"gadget rect not found\"; else type -b \"gadget rect assigned\";",
                        "type -b \"Running Quick Peaks step: gettree\"; tree trgui; gg.gettree(trgui); type -b \"gettree done\";",
                        "type -b \"Running Quick Peaks step: apply tree settings\"; trgui.output.resultwks$ = \"[QkPeak]Result\"; trgui.output.tagwks$ = \"[QkPeak]Tag\"; trgui.output.baselinewks$ = \"[QkPeak]Baseline\"; gg.settree(trgui); type -b \"settree done\";",
                        "type -b \"Running Quick Peaks step: slide ROI and output\"; for (int i=0;i<=10;i++){ double xPos = 1!1.xmin + i*(1!1.xmax-1!1.xmin)/10; gg.x = xPos; type -b \"ROI->%{xPos}\"; gg.output(4); delay 1; }; type -b \"slide done\";"
                    ]
                    for i, s in enumerate(steps, start=1):
                        print(f'Executing LabTalk step {i}/{len(steps)}...')
                        r = op.lt_exec(s)
                        print(f'Step {i} returned:', repr(r))
                        time.sleep(0.5)

                    # If sliding step failed to produce worksheets, probe gg.output modes 0..6
                    print('Probing gg.output modes 0..6 to find a working output call...')
                    for mode in range(0, 7):
                        probe_cmd = f'gadget gg = rect; type -b "try output mode {mode}"; try {{ gg.output({mode}); type -b "output mode {mode} ok"; }} catch {{ type -b "output mode {mode} failed"; }}'
                        r = op.lt_exec(probe_cmd)
                        print(f'probe output mode {mode} returned:', repr(r))
                        time.sleep(0.3)
                except Exception as e:
                    print('Exception while executing LabTalk in Origin (multi-step):', e)
                    print('If Origin did not run the script, open the Script Window (Ctrl+Alt+S), paste the script', script_path)
                    print('and run it manually. Then re-run this script to export results.')
        except Exception as e:
            print('Error while running addtool_quickpeaks test:', e)
            print('Please open Origin Script Window, open', script_path, 'and run it manually.')
except Exception as e:
    print('Error invoking op.lt_exec for quick test:', e)
    print('Open Origin Script Window (Ctrl+Alt+S), open', script_path, 'and run it there. Paste the Script Window output here.')

# Wait a little for Origin to finish writing result worksheets
time.sleep(2)

after_sheets = list_workbook_sheets()
print('Worksheets after:', after_sheets)
new_sheets = [s for s in after_sheets if s not in before_sheets]
print('New worksheets detected:', new_sheets)

# Helper to export a worksheet to CSV if it exists
def export_wks_csv(sheet_name, out_path):
    try:
        wks = op.find_sheet('w', sheet_name)
    except Exception:
        wks = None
    if not wks:
        print(f'Worksheet {sheet_name} not found.')
        return None
    # Attempt to pull columns via to_list
    try:
        # Determine number of columns by attempting indices
        cols = []
        i = 0
        while True:
            try:
                col = wks.to_list(i)
            except Exception:
                break
            cols.append(col)
            i += 1
        # transpose into rows
        import pandas as _pd
        if not cols:
            print(f'No data in {sheet_name}')
            return None
        rows = list(zip(*cols))
        df = _pd.DataFrame(rows)
        df.to_csv(out_path, index=False, header=False)
        print(f'Exported {sheet_name} to {out_path}')
        return out_path
    except Exception as e:
        print('Error exporting', sheet_name, e)
        return None

# Export result/tag/baseline worksheets
os.makedirs('data', exist_ok=True)
export_wks_csv('[QkPeak]Result', os.path.join('data', 'QkPeak_Result.csv'))
export_wks_csv('[QkPeak]Tag', os.path.join('data', 'QkPeak_Tag.csv'))
export_wks_csv('[QkPeak]Baseline', os.path.join('data', 'QkPeak_Baseline.csv'))

print('Done. Check data/QkPeak_Result.csv etc. for exported results.')