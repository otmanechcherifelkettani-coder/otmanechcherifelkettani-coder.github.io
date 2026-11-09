// Shared 3D kit for "Shipping AI That Works" (university edition)
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

export const C = {
  blue: 0x1f5bff, orange: 0xff6a2b, yellow: 0xffc83d, mint: 0x52dcae, paper: 0xfbf4e8, navy: 0x11204a, sky: 0xd9e4ff, white: 0xffffff,
};
export const CSS = { blue: '#1F5BFF', orange: '#FF6A2B', yellow: '#FFC83D', mint: '#52DCAE', paper: '#FBF4E8', navy: '#11204A', sky: '#D9E4FF' };

const mat = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: o.r ?? .45, metalness: 0, emissive: o.e ?? 0x000000, emissiveIntensity: o.ei ?? 1 });

// 8-point star (khatam) = two overlapping squares rotated 45 degrees
export function starShape(r = .5, inner = .38) {
  const s = new THREE.Shape(); const n = 16;
  for (let i = 0; i < n; i++) {
    const a = Math.PI / 2 + i * Math.PI * 2 / n; const rr = i % 2 ? r * .6 : r;
    const x = Math.cos(a) * rr, y = Math.sin(a) * rr; i ? s.lineTo(x, y) : s.moveTo(x, y);
  }
  s.closePath(); return s;
}
export function star(color = C.orange, r = .5, depth = .1) {
  const g = new THREE.ExtrudeGeometry(starShape(r), { depth, bevelEnabled: true, bevelThickness: .03, bevelSize: .03, bevelSegments: 4, curveSegments: 4 });
  g.center(); const m = new THREE.Mesh(g, mat(color, { r: .35 })); m.castShadow = true; return m;
}

// ---------- NAJMA, the agent ----------
export function makeAgent(opts = {}) {
  const color = opts.color ?? C.blue;
  const root = new THREE.Group(); const rig = new THREE.Group(); root.add(rig);
  const body = new THREE.Mesh(new RoundedBoxGeometry(1.3, 1.15, 1.05, 8, .42), mat(color, { r: .38 }));
  body.castShadow = true; rig.add(body);
  const face = new THREE.Mesh(new RoundedBoxGeometry(1.0, .6, .12, 6, .06), mat(C.navy, { r: .25 }));
  face.position.set(0, .07, .5); rig.add(face);
  const eyeMat = mat(C.mint, { e: C.mint, ei: .55, r: .3 });
  const eyes = [-1, 1].map(s => { const e = new THREE.Mesh(new THREE.CapsuleGeometry(.075, .13, 8, 16), eyeMat); e.position.set(s * .2, .08, .575); rig.add(e); return e; });
  const happy = [-1, 1].map(s => { const e = new THREE.Mesh(new THREE.TorusGeometry(.085, .032, 10, 24, Math.PI), eyeMat); e.position.set(s * .2, .05, .575); e.visible = false; rig.add(e); return e; });
  const cheeks = [-1, 1].map(s => { const c = new THREE.Mesh(new THREE.CircleGeometry(.06, 24), new THREE.MeshBasicMaterial({ color: C.orange, transparent: true, opacity: .0 })); c.position.set(s * .36, -.08, .57); rig.add(c); return c; });
  const badge = star(C.orange, .26, .07); badge.position.set(0, .86, 0); rig.add(badge);
  const hands = [-1, 1].map(s => { const h = new THREE.Mesh(new THREE.SphereGeometry(.15, 32, 16), mat(C.yellow, { r: .4 })); h.castShadow = true; h.position.set(s * .88, -.12, .1); rig.add(h); return h; });
  root.userData = { rig, body, eyes, happy, cheeks, badge, hands };
  return root;
}
// pose: {bob, look:[x,y], blink 0..1, happy bool, wave 0..1, tilt, squash}
export function poseAgent(a, p = {}, t = 0) {
  const u = a.userData;
  u.rig.position.y = (p.bob ?? .06) * Math.sin(t * 2.4) + (p.lift ?? 0);
  u.rig.rotation.z = (p.tilt ?? 0); u.rig.rotation.y = (p.turn ?? 0);
  const sq = p.squash ?? 0; u.rig.scale.set(1 + sq * .5, 1 - sq, 1 + sq * .5);
  const [lx, ly] = p.look ?? [0, 0];
  u.eyes.forEach((e, i) => { e.position.x = (i ? .2 : -.2) + lx * .06; e.position.y = .08 + ly * .05; e.scale.y = 1 - .9 * (p.blink ?? 0); e.visible = !p.happy; });
  u.happy.forEach((e, i) => { e.visible = !!p.happy; e.position.x = (i ? .2 : -.2) + lx * .06; });
  u.cheeks.forEach(c => c.material.opacity = p.happy ? .85 : 0);
  u.badge.rotation.y = t * 1.6 + (p.starSpin ?? 0);
  const w = p.wave ?? 0;
  u.hands[1].position.set(.88 + .1 * w, -.12 + .55 * w + .12 * w * Math.sin(t * 9), .1 + .1 * w);
  u.hands[0].position.set(-.88 - (p.reach ?? 0) * .1, -.12 + (p.reach ?? 0) * .25, .1 + (p.reach ?? 0) * .45);
}

// ---------- world ----------
export function makeWorld(renderer, w, h, opts = {}) {
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05; renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene(); scene.background = opts.transparent ? null : new THREE.Color(opts.bg ?? C.paper);
  const cam = new THREE.PerspectiveCamera(opts.fov ?? 30, w / h, .1, 200);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xf3d9b8, 1.6));
  const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(4, 8, 6); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); key.shadow.camera.left = -12; key.shadow.camera.right = 12; key.shadow.camera.top = 12; key.shadow.camera.bottom = -12; key.shadow.radius = 6; key.shadow.bias = -.0005;
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xdfe8ff, .8); rim.position.set(-6, 4, -4); scene.add(rim);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.ShadowMaterial({ opacity: .11 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -.9; ground.receiveShadow = true; if (!opts.noGround) scene.add(ground);
  return { scene, cam, ground };
}

// ---------- props ----------
export const P = {
  ball: (c = C.yellow, r = .4) => shadow(new THREE.Mesh(new THREE.SphereGeometry(r, 48, 24), mat(c))),
  ring: (c = C.mint, r = .45, t = .16) => shadow(new THREE.Mesh(new THREE.TorusGeometry(r, t, 24, 64), mat(c))),
  cone: (c = C.orange, r = .42, h = .8) => shadow(new THREE.Mesh(new THREE.ConeGeometry(r, h, 64), mat(c))),
  pill: (c = C.blue, r = .2, l = .6) => shadow(new THREE.Mesh(new THREE.CapsuleGeometry(r, l, 12, 32), mat(c))),
  cube: (c = C.sky, s = .7, rad = .14) => shadow(new THREE.Mesh(new RoundedBoxGeometry(s, s, s, 6, rad), mat(c))),
  slab: (c, w, h, d = .12, rad = .05) => shadow(new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 6, rad), mat(c))),
  star: (c = C.orange, r = .4, d = .12) => star(c, r, d),
};
function shadow(m) { m.castShadow = true; m.receiveShadow = true; return m; }

// labelled block: rounded cube with text drawn on its front face
export function wordBlock(text, bg, fg, w = 1.6, h = .62, d = .5) {
  const g = new THREE.Group(); const box = P.slab(bg, w, h, d, .12); g.add(box);
  const cv = document.createElement('canvas'); cv.width = 512 * w / h | 0; cv.height = 512; const x = cv.getContext('2d');
  x.fillStyle = fg; x.font = `800 ${cv.height * .42}px Brico`; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(text, cv.width / 2, cv.height * .54);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(w * .92, h * .92), new THREE.MeshBasicMaterial({ map: tex, transparent: true }));
  plane.position.z = d / 2 + .002; g.add(plane); return g;
}
// tool tile: flat rounded slab with icon + code label on top face
export function toolTile(label, color, icon) {
  const g = new THREE.Group(); const s = P.slab(C.white, 2.2, .7, .16, .08); g.add(s);
  const cv = document.createElement('canvas'); cv.width = 1100; cv.height = 350; const x = cv.getContext('2d');
  x.fillStyle = color; roundRect(x, 30, 75, 200, 200, 48); x.fill();
  x.strokeStyle = '#fff'; x.lineWidth = 14; x.lineCap = 'round'; x.lineJoin = 'round'; icon(x, 130, 175);
  x.fillStyle = CSS.navy; x.font = '600 70px JBM'; x.textBaseline = 'middle'; x.fillText(label, 270, 180);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  const p = new THREE.Mesh(new THREE.PlaneGeometry(2.1, .668), new THREE.MeshBasicMaterial({ map: tex, transparent: true })); p.position.z = .081; g.add(p);
  return g;
}
export function roundRect(x, a, b, w, h, r) { x.beginPath(); x.moveTo(a + r, b); x.arcTo(a + w, b, a + w, b + h, r); x.arcTo(a + w, b + h, a, b + h, r); x.arcTo(a, b + h, a, b, r); x.arcTo(a, b, a + w, b, r); x.closePath(); }
export const ICON = {
  search: (x, cx, cy) => { x.beginPath(); x.arc(cx - 12, cy - 12, 42, 0, 7); x.stroke(); x.beginPath(); x.moveTo(cx + 20, cy + 20); x.lineTo(cx + 55, cy + 55); x.stroke(); },
  shield: (x, cx, cy) => { x.beginPath(); x.moveTo(cx, cy - 60); x.lineTo(cx + 50, cy - 40); x.lineTo(cx + 50, cy + 5); x.quadraticCurveTo(cx + 45, cy + 45, cx, cy + 62); x.quadraticCurveTo(cx - 45, cy + 45, cx - 50, cy + 5); x.lineTo(cx - 50, cy - 40); x.closePath(); x.stroke(); x.beginPath(); x.moveTo(cx - 20, cy); x.lineTo(cx - 3, cy + 18); x.lineTo(cx + 25, cy - 15); x.stroke(); },
  card: (x, cx, cy) => { roundRect(x, cx - 60, cy - 40, 120, 80, 12); x.stroke(); x.beginPath(); x.moveTo(cx - 60, cy - 12); x.lineTo(cx + 60, cy - 12); x.stroke(); },
  person: (x, cx, cy) => { x.beginPath(); x.arc(cx, cy - 22, 24, 0, 7); x.stroke(); x.beginPath(); x.moveTo(cx - 48, cy + 55); x.quadraticCurveTo(cx, cy - 10, cx + 48, cy + 55); x.stroke(); },
  sync: (x, cx, cy) => { x.beginPath(); x.arc(cx, cy, 44, -2.6, 1.2); x.stroke(); x.beginPath(); x.moveTo(cx + 22, cy + 48); x.lineTo(cx + 18, cy + 30); x.lineTo(cx + 38, cy + 26); x.stroke(); },
};

// drink cup (the missing item in the SoukGo case)
export function cup() {
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.CylinderGeometry(.26, .2, .62, 48), mat(C.mint)); b.castShadow = true; g.add(b);
  const lid = new THREE.Mesh(new THREE.CylinderGeometry(.29, .29, .07, 48), mat(C.white)); lid.position.y = .34; lid.castShadow = true; g.add(lid);
  const straw = new THREE.Mesh(new THREE.CylinderGeometry(.03, .03, .45, 16), mat(C.orange)); straw.position.set(.06, .55, 0); straw.rotation.z = -.25; g.add(straw);
  return g;
}
// delivery box with tape
export function box() {
  const g = new THREE.Group(); const b = P.slab(C.orange, 1.0, .72, .8, .08); g.add(b);
  const tape = new THREE.Mesh(new RoundedBoxGeometry(.22, .74, .82, 2, .02), mat(C.yellow)); g.add(tape);
  return g;
}
