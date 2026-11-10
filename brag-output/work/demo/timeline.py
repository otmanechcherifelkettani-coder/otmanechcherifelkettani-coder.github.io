"""Place the VO lines on the timeline; write tl.js (read by film.html) and tl.json (read by the mix)."""
import json
d = json.load(open('vo/dur.json')); D = {int(k): v for k, v in d['dur'].items()}
LEAD, TAIL = 0.9, 3.6
GAP = {1: .5, 2: 1.0, 3: .45, 4: .55, 5: 1.0, 6: .5, 7: .8, 8: .55, 9: 1.3, 10: .9, 11: .7, 12: .5, 13: .9, 14: .6, 15: 1.2, 16: .45, 17: .5, 18: 1.2, 19: .35, 20: .9}
T, t = {}, LEAD
for i in range(1, len(D) + 1):
    T[i] = round(t * 30) / 30; t = T[i] + D[i] + GAP.get(i, 0)
END = round((T[len(D)] + D[len(D)] + TAIL) * 30) / 30
json.dump({'T': T, 'D': D, 'END': END}, open('tl.json', 'w'))
open('tl.js', 'w').write('const T=' + json.dumps([0] + [T[i] for i in sorted(T)]) + ',D=' + json.dumps([0] + [D[i] for i in sorted(D)]) + ',END=' + str(END) + ';\n')
print(T, END)
