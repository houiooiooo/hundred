"""Human Design type frequency simulation (reproducible).
Usage: python3 hd.py START_YEAR END_YEAR N SEED
"""
import sys, random
import swisseph as swe

FLAG = swe.FLG_MOSEPH  # built-in Moshier ephemeris, no data files
WHEEL = [41,19,13,49,30,55,37,63,22,36,25,17,21,51,42,3,27,24,2,23,8,20,16,35,45,12,15,52,39,53,
         62,56,31,33,7,4,29,59,40,64,47,6,46,18,48,57,32,50,28,44,1,43,14,34,9,5,26,11,10,58,38,54,61,60]
START = 302.0  # gate 41 begins at 2 deg Aquarius (tropical)

CENTER = {}
for c, gs in {
    'head':[64,61,63], 'ajna':[47,24,4,17,43,11],
    'throat':[62,23,56,35,12,45,33,8,31,20,16], 'g':[7,1,13,10,25,46,2,15],
    'heart':[21,40,26,51], 'sp':[36,22,37,6,49,55,30],
    'sacral':[34,5,14,29,59,9,3,42,27], 'spleen':[48,57,44,50,32,28,18],
    'root':[53,60,52,19,39,41,58,38,54]}.items():
    for g in gs: CENTER[g] = c
assert len(CENTER) == 64
CHANNELS = [(64,47),(61,24),(63,4),(17,62),(43,23),(11,56),(31,7),(8,1),(33,13),(45,21),(35,36),
            (12,22),(20,34),(16,48),(20,57),(10,20),(25,51),(2,14),(15,5),(46,29),(10,34),(10,57),
            (26,44),(37,40),(50,27),(34,57),(59,6),(42,53),(3,60),(9,52),(32,54),(28,38),(18,58),
            (19,49),(39,55),(41,30)]
assert len(CHANNELS) == 36

def gate(lon):
    return WHEEL[int(((lon - START) % 360) / 5.625)]

def positions(jd):
    sun = swe.calc_ut(jd, swe.SUN, FLAG)[0][0]
    lons = [sun, (sun + 180) % 360]
    node = swe.calc_ut(jd, swe.TRUE_NODE, FLAG)[0][0]
    lons += [node, (node + 180) % 360]
    for p in (swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN,
              swe.URANUS, swe.NEPTUNE, swe.PLUTO):
        lons.append(swe.calc_ut(jd, p, FLAG)[0][0])
    return lons, sun

def design_jd(jd, sun):
    target = (sun - 88.0) % 360
    t = jd - 88.0  # sun moves ~1 deg/day; refine by Newton steps
    for _ in range(30):
        s = swe.calc_ut(t, swe.SUN, FLAG)[0][0]
        d = ((s - target + 180) % 360) - 180
        if abs(d) < 1e-6: break
        t -= d / 0.9856
    return t

def htype(jd):
    p, sun = positions(jd)
    d, _ = positions(design_jd(jd, sun))
    gates = {gate(x) for x in p + d}
    adj = {}
    defined = set()
    for a, b in CHANNELS:
        if a in gates and b in gates:
            ca, cb = CENTER[a], CENTER[b]
            defined |= {ca, cb}
            adj.setdefault(ca, set()).add(cb); adj.setdefault(cb, set()).add(ca)
    if not defined: return 'Reflector'
    # throat connected to a motor?
    seen, stack = {'throat'}, ['throat']
    while stack:
        for n in adj.get(stack.pop(), ()):
            if n not in seen: seen.add(n); stack.append(n)
    motor_throat = bool(seen & {'sacral','heart','sp','root'}) and 'throat' in defined
    if 'sacral' in defined:
        return 'Manifesting Generator' if motor_throat else 'Generator'
    return 'Manifestor' if motor_throat else 'Projector'

if __name__ == '__main__':
    y0, y1, n, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    rng = random.Random(seed)
    j0 = swe.julday(y0, 1, 1, 0); j1 = swe.julday(y1 + 1, 1, 1, 0)
    cnt = {}
    for _ in range(n):
        t = htype(rng.uniform(j0, j1))
        cnt[t] = cnt.get(t, 0) + 1
    for k in ['Generator','Manifesting Generator','Projector','Manifestor','Reflector']:
        print(f"{y0}-{y1}\t{k}\t{cnt.get(k,0)}\t{100*cnt.get(k,0)/n:.1f}%")
