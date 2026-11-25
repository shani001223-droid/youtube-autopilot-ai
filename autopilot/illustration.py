"""Original stylized scenery, generated locally without an external service."""
import hashlib, random, math
from PIL import Image, ImageDraw, ImageFilter

def draw_scene(query, path, index=0):
    seed=int.from_bytes(hashlib.sha256(f"{query}:{index}".encode()).digest()[:8],"big")
    rng=random.Random(seed)
    w,h=720,1280
    img=Image.new("RGB",(w,h)); d=ImageDraw.Draw(img)
    palette=[((20,38,55),(78,99,112)),((36,29,48),(104,78,83)),((18,43,41),(77,103,92))]
    a,b=palette[seed%len(palette)]
    for y in range(h):
        t=math.sin(math.pi*y/h)
        d.line((0,y,w,y),fill=tuple(int(x+(z-x)*t) for x,z in zip(a,b)))
    q=query.lower()
    inside=any(k in q for k in ("hall","room","door","house","window","shelf","archive","tape","reel","paper","floor","ledger","interior","stairs","radio","mirror","clock"))
    if inside:
        # Perspective corridor, practical lights and a central object.
        vx,vy=w//2,int(h*.43)
        d.polygon([(0,0),(vx,vy),(vx,h),(0,h)],fill=(29,35,43))
        d.polygon([(w,0),(vx,vy),(vx,h),(w,h)],fill=(39,43,48))
        d.polygon([(0,h),(vx,vy),(w,h)],fill=(55,61,65))
        for x in range(-w,w*2,100): d.line((vx,vy,x,h),fill=(76,81,81),width=3)
        for k in (0.22,.43,.62,.80):
            x=int(vx*k); yy=int(vy*k); bottom=int(h-(h-vy)*k)
            d.line((x,yy,x,bottom),fill=(81,87,87),width=5)
            d.line((w-x,yy,w-x,bottom),fill=(81,87,87),width=5)
        d.rectangle((265,425,455,855),fill=(12,21,29),outline=(118,126,120),width=8)
        d.rectangle((291,452,429,831),fill=(36,48,55),outline=(66,78,80),width=3)
        d.ellipse((400,649,414,663),fill=(196,156,91))
        if any(k in q for k in ("tape","reel","radio","paper","ledger","clock")):
            d.rounded_rectangle((136,670,584,1000),20,fill=(76,75,69),outline=(157,143,113),width=5)
            if any(k in q for k in ("paper","ledger")):
                d.polygon([(180,700),(365,730),(540,700),(540,939),(365,975),(180,939)],fill=(183,169,128))
                for y in range(750,930,22): d.line((205,y,345,y+18),fill=(94,88,70),width=3); d.line((386,y+18,516,y),fill=(94,88,70),width=3)
            else:
                for x in (255,465):
                    d.ellipse((x-85,700,x+85,870),fill=(41,45,45),outline=(177,168,138),width=8)
                    for angle in (0,120,240):
                        xx=x+int(49*math.cos(math.radians(angle))); yy=785+int(49*math.sin(math.radians(angle)))
                        d.ellipse((xx-20,yy-20,xx+20,yy+20),fill=(104,112,108))
                d.rectangle((220,914,500,950),fill=(28,42,40))
                d.ellipse((470,922,486,938),fill=(204,92,52))
    else:
        mx,my=rng.randint(160,560),rng.randint(180,350)
        glow=Image.new("RGB",(w,h)); gd=ImageDraw.Draw(glow)
        gd.ellipse((mx-110,my-110,mx+110,my+110),fill=(98,112,115))
        glow=glow.filter(ImageFilter.GaussianBlur(45))
        from PIL import ImageChops
        img=ImageChops.add(img,glow); d=ImageDraw.Draw(img)
        d.ellipse((mx-45,my-45,mx+45,my+45),fill=(184,197,188))
        for level in range(3):
            y=600+level*150
            pts=[(0,h),(0,y)]+[(x,y+rng.randint(-85,85)) for x in range(0,w+100,80)]+[(w,h)]
            d.polygon(pts,fill=(34-level*7,51-level*8,57-level*8))
        if any(k in q for k in ("lighthouse","sea","coast","ocean")):
            d.polygon([(280,930),(330,430),(395,430),(450,930)],fill=(95,101,95))
            d.rectangle((321,375,403,445),fill=(182,167,112),outline=(43,50,53),width=7)
            d.polygon([(306,375),(362,320),(419,375)],fill=(37,45,49))
            d.polygon([(404,387),(720,290),(720,480),(404,417)],fill=(107,124,115))
        else:
            for layer in range(3):
                for j in range(9):
                    x=rng.randint(-30,w+30); base=930+layer*115; top=base-rng.randint(180,500)
                    c=(26-layer*5,43-layer*7,44-layer*6)
                    d.rectangle((x-5,top,x+5,base),fill=c)
                    for k in range(4):
                        y=top+k*45; spread=24+k*15
                        d.polygon([(x,y-30),(x-spread,y+105),(x+spread,y+105)],fill=c)
            d.polygon([(300,h),(415,h),(370,825),(350,825)],fill=(80,91,89))
    fog=Image.new("RGBA",(w,h)); fd=ImageDraw.Draw(fog)
    for i in range(12):
        y=rng.randint(350,h); fd.ellipse((-200,y,w+200,y+rng.randint(20,100)),fill=(150,169,170,rng.randint(14,39)))
    fog=fog.filter(ImageFilter.GaussianBlur(25))
    img=Image.alpha_composite(img.convert("RGBA"),fog).convert("RGB")
    img.save(path,"JPEG",quality=92)
