import os
import originpro as op

op.set_show()

x_vals = [1,2,3,4,5,6,7,8,9,10]
y_vals = [23,45,78,133,178,199,234,278,341,400]

wks = op.new_sheet('w')

wks.from_list(0, x_vals, 'X Values')
wks.from_list(1, y_vals, 'Y Values')

gp = op.new_graph()
gl = gp[0]
gl.add_plot(wks, 1, 0)
gl.rescale()

fpath = op.path('u') + 'simple.png'
gp.save_fig(fpath)
print(f'{gl} is exported as {fpath}')

op.exit()