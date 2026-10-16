"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

FIGURES = ('switching-relations', 'tail-continuation', 'certificate-pipeline',
           'region-partition', 'trust-boundary')

def render(out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    d=Drawing((-2.0,-1.0,10.5,2.0))
    d.box('a',0,0,3.5,1.3,'allocation relation\n'+r'$\simeq_A$'+'\ninitialized allocation')
    d.box('c',4.3,0,3.5,1.3,'contextual equivalence\n'+r'$\simeq_{\mathrm{ctx}}$'+'\nall continuations')
    d.box('f',8.6,0,3.5,1.3,'observation relation '+r'$R_K$'+'\nsame continuation '+r'$K$'+'\nmay be coarser')
    d.edge('a','c','e','w');d.edge('c','a','w','e')
    d.text(2.15,1.1,'exact');d.edge('c','f','e','w')
    d.text(6.45,1.1,'fix the same '+r'$K$')
    d.save(out,'switching-relations')

    d=Drawing((-1.7,-1.9,8.1,2.6))
    d.text(-.6,1.5,'initial',ha='right')
    def cells(x,y,values):
        for k,t in enumerate(values):
            d.box(str((x,y,k)),x+.65*k,y,.65,.55,'$'+t+'$')
    cells(0,1.5,['0','x','0']);cells(5,1.5,['0','0','0'])
    d.arrow((1.8,1.5),(4.5,1.5));d.text(3.15,1.9,'erase tail')
    for x in (.65,5.65):
        d.arrow((x,1.1),(x,.25))
        d.text(x+(.8 if x>1 else -.8),.7,'store 1 at 0')
    cells(0,-.15,['1','x','0']);cells(5,-.15,['1','0','0'])
    d.text(.65,-1.1,r'length = 1 if $x=0$'+'\n'+r'length = 2 if $x\ne0$')
    d.text(5.65,-1.1,'length = 1\nfor every byte '+r'$x$')
    d.save(out,'tail-continuation')

    d=Drawing((-1.9,-4.2,10.55,2.35))
    for n,x,y,label in [
        ('s',0,0,'paired statement\nand input schema'),
        ('p',4.3,0,'producer\ngraph solver + executor'),
        ('c',8.6,0,'JSON certificate\nsplits, leaves, minima'),
        ('r',8.6,-1.7,'replayer\nrelaxation + evaluator'),
        ('v',4.3,-1.7,'checked verdict\nor rejection'),
        ('ps',4.3,1.65,'equality contraction\ntopological minimum'),
        ('rs',8.6,-3.35,'endpoint relaxation\nrecomputed minimum')]:
        d.box(n,x,y,3.5,1.15,label)
    d.edge('s','p','e','w');d.edge('p','c','e','w')
    d.edge('c','r');d.edge('r','v','w','e')
    d.edge('ps','p',dashed=True);d.edge('rs','r','n','s',dashed=True)
    d.save(out,'certificate-pipeline')

    d=Drawing((-4.3,-3.55,4.3,.65))
    d.box('r',0,0,1,.65,r'$\mathcal{R}$')
    for n,x,label,answer in [('a',-2.8,r'$\mathcal{R}\wedge x<y$','<'),
                            ('b',0,r'$\mathcal{R}\wedge x=y$','='),
                            ('c',2.8,r'$\mathcal{R}\wedge x>y$','>')]:
        d.box(n,x,-1.4,2.45,.7,label)
        d.edge('r',n);d.text(x*.55+.16,-.65,'$'+answer+'$')
        d.arrow((x,-1.75),(x,-2.15))
        d.text(x,-2.4,'check domain')
    d.text(0,-3.1,'feasible: checked continuation     empty: no child')
    d.save(out,'region-partition')

    d=Drawing((-1.85,-1.85,10.1,2.75))
    for n,x,y,label in [
        ('m',0,0,'paper model\ndefinitions and proofs'),
        ('p',4.05,1,'certificate producer\nuntrusted for acceptance'),
        ('r',4.05,-1,'certificate replayer\ntrusted implementation'),
        ('py',8.1,-1,'Python runtime and OS\ntrusted execution base'),
        ('o',8.1,1,'C/LLVM and\nSMT translation')]:
        d.box(n,x,y,3.55,1.15,label)
    d.edge('m','p','e','w');d.edge('m','r','e','w')
    d.edge('p','r');d.text(4.25,0,'certificate',ha='left',size=8)
    d.edge('r','py','e','w')
    d.line([(0,.575),(0,2.15),(8.1,2.15),(8.1,1.575)],dashed=True)
    d.text(4.05,2.45,'no established model correspondence',size=8)
    d.save(out,'trust-boundary')

def main():
    parser=argparse.ArgumentParser(description='Generate the five semantic diagrams directly as vector PDF.')
    parser.add_argument('--outdir',type=Path,required=True)
    args=parser.parse_args()
    render(args.outdir)

if __name__=='__main__':
    main()
