import json

with open('projects/leather_blazer/measurements.json') as f:
    M = json.load(f)

chest = M['chest'] * 10
waist = M['waist'] * 10
hip = M['hip'] * 10
shoulder = M['shoulder'] * 10
sleeve_length = M['sleeve_length'] * 10
back_length = M['back_length'] * 10
bicep = M['bicep'] * 10

# geometry helpers
def rectangle(x,y,w,h):
    return [(x,y),(x+w,y),(x+w,y+h),(x,y+h)]

entities = []

def add_lwpolyline(points, layer, closed=True):
    ent = ['0','LWPOLYLINE','8',layer,'90',str(len(points))]
    if closed:
        ent.extend(['70','1'])
    for x,y in points:
        ent.extend(['10',f'{x}','20',f'{y}'])
    entities.append(ent)

def add_line(x1,y1,x2,y2,layer):
    entities.append(['0','LINE','8',layer,'10',f'{x1}','20',f'{y1}','11',f'{x2}','21',f'{y2}'])

def add_text(x,y,text,layer):
    entities.append(['0','TEXT','8',layer,'10',f'{x}','20',f'{y}','40','10','1',text])

def add_circle(x,y,r,layer):
    entities.append(['0','CIRCLE','8',layer,'10',f'{x}','20',f'{y}','40',f'{r}'])

# start geometry
cur_x = 150
cur_y = 0
spacing_x = 50
spacing_y = 150

def piece(name,w,h,ox,oy):
    base = rectangle(ox,oy,w,h)
    add_lwpolyline(base,'CUT')
    sa = rectangle(ox-8,oy-8,w+16,h+16)
    add_lwpolyline(sa,'SA')
    ts = rectangle(ox+3.5,oy+3.5,w-7,h-7)
    add_lwpolyline(ts,'TOPSTITCH')
    add_line(ox+w/2,oy+10,ox+w/2,oy+h-10,'GRAIN')
    add_text(ox+5,oy+h/2,name,'TEXT')
    return (ox,oy,w,h)

# Test square
add_lwpolyline(rectangle(0,0,100,100),'CUT')

front_w = chest/4 + 20
back_w = chest/4 + 15
side_w = 100
front = piece('Front',front_w,back_length,cur_x,cur_y)
back = piece('Back',back_w,back_length,cur_x+front_w+spacing_x,cur_y)
side = piece('Side Panel',side_w,back_length,cur_x+front_w+back_w+spacing_x*2,cur_y)
vent_u = piece('Vent Underlay',60,240,cur_x+front_w+back_w+side_w+spacing_x*3,cur_y)
vent_o = piece('Vent Overlap',60,240,cur_x+front_w+back_w+side_w+spacing_x*3+80,cur_y)
upper = piece('Upper Sleeve',bicep*0.6,sleeve_length,cur_x,cur_y+back_length+spacing_y)
lower = piece('Lower Sleeve',bicep*0.4,sleeve_length,cur_x+bicep*0.6+spacing_x,cur_y+back_length+spacing_y)
upper_col = piece('Upper Collar',180,80,cur_x,cur_y+back_length+sleeve_length+spacing_y*2)
lower_col = piece('Lower Collar',180,80,cur_x+200,cur_y+back_length+sleeve_length+spacing_y*2)
front_facing = piece('Front Facing',65,back_length,cur_x+front_w*2+spacing_x*3,cur_y)
back_facing = piece('Back Facing',back_w,80,cur_x+front_w*2+spacing_x*3,cur_y+back_length+spacing_y)
pocket_flap = piece('Pocket Flap',150,60,cur_x+front_w*2+spacing_x*4,cur_y)
pocket_bag = piece('Pocket Bag',180,200,cur_x+front_w*2+spacing_x*4,cur_y+80)
front_lin = piece('Front Lining',front_w,back_length,cur_x+front_w*2+spacing_x*5,cur_y)
back_lin = piece('Back Lining',back_w,back_length,cur_x+front_w*2+spacing_x*5+front_w+spacing_x,cur_y)
side_lin = piece('Side Lining',side_w,back_length,cur_x+front_w*2+spacing_x*5+front_w+back_w+spacing_x*2,cur_y)
sleeve_lin = piece('Sleeve Lining',bicep*0.5,sleeve_length,cur_x+front_w*2+spacing_x*5,cur_y+back_length+spacing_y)
inside_pocket = piece('Inside Pocket',160,180,cur_x+front_w*2+spacing_x*5+front_w+back_w+spacing_x*2+side_w+spacing_x,cur_y)

# Notches
def notch(x,y):
    add_line(x-2.5,y,x+2.5,y,'NOTCH')

notch(front[0]+front[2]/2, front[1]+front[3])
notch(back[0]+back[2]/2, back[1]+back[3])
notch(front[0]+front[2], front[1]+back_length*0.6)
notch(back[0], back[1]+back_length*0.6)
notch(front[0]+front[2], front[1]+back_length*0.5)
notch(back[0], back[1]+back_length*0.5)
notch(front[0], front[1]+back_length*0.5)
notch(back[0]+back[2]/2, back[1]+240)
notch(back[0]+back[2]/2, back[1])

# Buttons
btn_x = front[0]+12
add_circle(btn_x, front[1]+400, 1,'PUNCH')
add_circle(btn_x, front[1]+500, 1,'PUNCH')

# Folds & skives
add_line(front[0],front[1],front[0],front[1]+back_length,'FOLD')
add_line(front[0]+14,front[1],front[0]+14,front[1]+back_length,'SKIVE')
add_line(pocket_flap[0],pocket_flap[1],pocket_flap[0]+150,pocket_flap[1],'FOLD')
add_line(pocket_flap[0],pocket_flap[1]+60,pocket_flap[0]+150,pocket_flap[1]+60,'FOLD')
add_line(pocket_flap[0],pocket_flap[1]+6,pocket_flap[0]+150,pocket_flap[1]+6,'SKIVE')
add_line(pocket_flap[0],pocket_flap[1]+54,pocket_flap[0]+150,pocket_flap[1]+54,'SKIVE')

# Write DXF
layers = ['CUT','SA','NOTCH','TOPSTITCH','FOLD','SKIVE','PUNCH','GRAIN','TEXT']
with open('projects/leather_blazer/outputs/blazer_pattern.dxf','w') as f:
    f.write('0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n')
    f.write('0\nSECTION\n2\nTABLES\n')
    f.write('0\nTABLE\n2\nLAYER\n70\n{}\n'.format(len(layers)))
    for i,layer in enumerate(layers):
        f.write('0\nLAYER\n2\n{}\n70\n0\n62\n{}\n6\nCONTINUOUS\n'.format(layer,7+i))
    f.write('0\nENDTAB\n0\nENDSEC\n')
    f.write('0\nSECTION\n2\nENTITIES\n')
    for ent in entities:
        f.write('\n'.join(ent)+'\n')
    f.write('0\nENDSEC\n0\nEOF')
