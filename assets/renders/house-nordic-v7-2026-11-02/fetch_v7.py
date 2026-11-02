#!/usr/bin/env python3
"""Download a finished var2 image (result URL) to the job's raw path and run process_v7.py on it. 0 tokens.
usage: python3 fetch_v7.py <job id> <result url>"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
J = json.load(open(os.path.join(HERE, 'jobs.json')))
jid, url = sys.argv[1:3]
job = next(j for j in J['jobs'] if j['id'] == jid)
ext = os.path.splitext(url.split('?')[0])[1].lower() or '.png'
out_dir = os.path.join(REPO, job['out_dir'])
os.makedirs(os.path.join(out_dir, 'raw'), exist_ok=True)
dl = os.path.join('/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/dl-results', jid + ext)
os.makedirs(os.path.dirname(dl), exist_ok=True)
r = subprocess.run(['curl', '-sS', '-L', '--max-time', '180', '-o', dl, '-w', '%{http_code}', url], capture_output=True, text=True)
print('GET', r.stdout.strip(), os.path.getsize(dl) if os.path.exists(dl) else None)
clay = os.path.join(REPO, J['clay'][job['frame']]['local'])
sc = os.path.join(REPO, 'assets/blockout/house/framing/round4/selfcheck.json')
subprocess.run(['python3.13', os.path.join(HERE, 'process_v7.py'), jid, dl, clay, job['frame'], out_dir, sc])
# overscan stills: the 16:9 frame (centre crop) and motion-agent's "16:9 + 6 % height" (the canvas cropped to the frame width)
os_ = job.get('overscan') or {}
if os_.get('on'):
    from PIL import Image
    g = Image.open(os.path.join(out_dir, jid + '-graded.png'))
    W, H = g.size
    cw, ch = os_['canvas_px']
    x0, y0, x1, y1 = os_['crop_box_px']
    fx0, fx1 = round(x0 / cw * W), round(x1 / cw * W)
    fy0, fy1 = round(y0 / ch * H), round(y1 / ch * H)
    g.crop((fx0, fy0, fx1, fy1)).save(os.path.join(out_dir, jid + '-frame.png'))
    g.crop((fx0, 0, fx1, H)).save(os.path.join(out_dir, jid + '-graded-os6.png'))
    J = json.load(open(os.path.join(HERE, 'jobs.json')))
    j2 = next(j for j in J['jobs'] if j['id'] == jid)
    j2['overscan'].update(output_canvas_px=[W, H], output_frame_box_px=[fx0, fy0, fx1, fy1], output_frame_px=[fx1 - fx0, fy1 - fy0],
                          output_os6_px=[fx1 - fx0, H], files=dict(canvas=job['out_dir'] + jid + '-graded.png', frame=job['out_dir'] + jid + '-frame.png',
                                                                   os6=job['out_dir'] + jid + '-graded-os6.png'),
                          motion_agent='-graded-os6.png = the 16:9 frame plus %.4f of its height above and below (--a-overscan / --b-overscan)' % (fy0 / (fy1 - fy0)))
    json.dump(J, open(os.path.join(HERE, 'jobs.json'), 'w'), indent=1, ensure_ascii=False)
    print('overscan crops: frame', fx1 - fx0, 'x', fy1 - fy0, '| os6', fx1 - fx0, 'x', H)
