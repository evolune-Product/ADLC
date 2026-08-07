/**
 * GLSL for the pipeline scene. Kept in one module so the noise implementation
 * is shared rather than pasted into each material.
 */

/** Ashima / Stefan Gustavson simplex noise (public domain). Drives the
 *  orchestrator core's surface. */
const SIMPLEX_3D = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}

float snoise(vec3 v){
  const vec2 C = vec2(1.0/6.0, 1.0/3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i  = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + C.yyy;
  vec3 x3 = x0 - D.yyy;
  i = mod289(i);
  vec4 p = permute(permute(permute(
             i.z + vec4(0.0, i1.z, i2.z, 1.0))
           + i.y + vec4(0.0, i1.y, i2.y, 1.0))
           + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 0.142857142857;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
  p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
`

/* ---------------------------------------------------------------- starfield */

export const STARFIELD_VERT = /* glsl */ `
uniform float uTime;
uniform float uPixelRatio;
uniform float uSize;

attribute float aScale;
attribute float aSeed;
attribute vec3 aColor;

varying float vAlpha;
varying vec3 vColor;

void main() {
  vec3 pos = position;

  // Very slow drift so the field is never quite still, without ever reading
  // as "moving".
  pos.x += sin(uTime * 0.06 + aSeed * 6.283) * 0.12;
  pos.y += cos(uTime * 0.05 + aSeed * 4.712) * 0.12;

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  // Perspective size attenuation: near stars are genuinely larger rather than
  // uniformly sized, which is most of what gives the field depth.
  gl_PointSize = uSize * aScale * uPixelRatio * (140.0 / max(-mvPosition.z, 0.001));

  float twinkle = 0.55 + 0.45 * sin(uTime * (0.7 + aSeed * 1.6) + aSeed * 12.0);
  float depthFade = smoothstep(90.0, 12.0, -mvPosition.z);
  vAlpha = twinkle * depthFade;
  vColor = aColor;
}
`

export const STARFIELD_FRAG = /* glsl */ `
uniform float uOpacity;

varying float vAlpha;
varying vec3 vColor;

void main() {
  // Round point with a soft core and a wide falloff — reads as a lit particle
  // rather than a square.
  float d = length(gl_PointCoord - vec2(0.5));
  if (d > 0.5) discard;
  float core = smoothstep(0.5, 0.0, d);
  float glow = pow(core, 2.6);
  gl_FragColor = vec4(vColor * (0.4 + glow), glow * vAlpha * uOpacity);
}
`

/* ------------------------------------------------------- orchestrator core */

export const CORE_VERT = /* glsl */ `
uniform float uTime;
uniform float uAmplitude;

varying vec3 vNormal;
varying vec3 vViewDir;
varying float vDisplacement;

${SIMPLEX_3D}

void main() {
  // Two octaves: a slow swell plus a faster fine ripple. The surface breathes
  // rather than wobbles, which is what separates "alive" from "animated".
  float slow = snoise(position * 1.15 + vec3(0.0, uTime * 0.16, 0.0));
  float fast = snoise(position * 3.4 - vec3(uTime * 0.28, 0.0, uTime * 0.13));
  float displacement = slow * 0.72 + fast * 0.28;

  vec3 displaced = position + normal * displacement * uAmplitude;

  vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  vNormal = normalize(normalMatrix * normal);
  vViewDir = normalize(-mvPosition.xyz);
  vDisplacement = displacement;
}
`

export const CORE_FRAG = /* glsl */ `
uniform vec3 uColorDeep;
uniform vec3 uColorLit;

varying vec3 vNormal;
varying vec3 vViewDir;
varying float vDisplacement;

void main() {
  // Fresnel rim: the edge lights up as it turns away, which is what makes a
  // sphere read as a volume with atmosphere rather than a flat disc.
  float fresnel = pow(1.0 - max(dot(normalize(vNormal), normalize(vViewDir)), 0.0), 2.4);

  // Crest lighting driven by the same displacement the vertex stage applied,
  // so the heat sits on the actual peaks of the surface — molten metal, not a
  // painted sphere.
  float crest = smoothstep(-0.25, 0.55, vDisplacement);

  vec3 color = mix(uColorDeep, uColorLit, crest * 0.62 + fresnel * 0.78);
  float alpha = 0.44 + fresnel * 0.56;

  gl_FragColor = vec4(color, alpha);
}
`
