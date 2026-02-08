"use client";

import { useRef, useEffect, useMemo, useCallback } from "react";
import * as THREE from "three";

interface ColorBendsProps {
  rotation?: number;
  autoRotate?: number;
  speed?: number;
  colors?: string[];
  transparent?: boolean;
  scale?: number;
  frequency?: number;
  warpStrength?: number;
  mouseInfluence?: number;
  parallax?: number;
  noise?: number;
  className?: string;
  style?: React.CSSProperties;
}

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  precision highp float;

  uniform float uTime;
  uniform float uRotation;
  uniform float uScale;
  uniform float uFrequency;
  uniform float uWarpStrength;
  uniform float uNoise;
  uniform vec2 uMouse;
  uniform float uMouseInfluence;
  uniform float uParallax;
  uniform vec3 uColors[8];
  uniform int uColorCount;
  uniform bool uTransparent;

  varying vec2 vUv;

  // Simplex noise function
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

  float snoise(vec2 v) {
    const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
    vec2 i = floor(v + dot(v, C.yy));
    vec2 x0 = v - i + dot(i, C.xx);
    vec2 i1;
    i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
    vec4 x12 = x0.xyxy + C.xxzz;
    x12.xy -= i1;
    i = mod289(i);
    vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
    vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
    m = m * m;
    m = m * m;
    vec3 x = 2.0 * fract(p * C.www) - 1.0;
    vec3 h = abs(x) - 0.5;
    vec3 ox = floor(x + 0.5);
    vec3 a0 = x - ox;
    m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
    vec3 g;
    g.x = a0.x * x0.x + h.x * x0.y;
    g.yz = a0.yz * x12.xz + h.yz * x12.yw;
    return 130.0 * dot(m, g);
  }

  mat2 rotate2d(float angle) {
    float s = sin(angle);
    float c = cos(angle);
    return mat2(c, -s, s, c);
  }

  void main() {
    vec2 uv = vUv - 0.5;

    // Apply parallax from mouse
    uv += uMouse * uParallax * 0.1;

    // Apply rotation
    uv = rotate2d(uRotation) * uv;

    // Scale
    uv *= uScale;

    // Create wave patterns
    float time = uTime * 0.5;

    // Mouse influence on distortion
    vec2 mouseEffect = uMouse * uMouseInfluence * 0.3;

    // Calculate warp
    float warp1 = sin(uv.x * uFrequency * 3.0 + time + mouseEffect.x) * uWarpStrength * 0.3;
    float warp2 = cos(uv.y * uFrequency * 2.5 + time * 0.7 + mouseEffect.y) * uWarpStrength * 0.3;
    float warp3 = sin((uv.x + uv.y) * uFrequency * 2.0 + time * 1.3) * uWarpStrength * 0.2;

    // Apply warping
    vec2 warpedUv = uv;
    warpedUv.x += warp1 + warp3;
    warpedUv.y += warp2 + warp3;

    // Add noise to warped UV
    float noiseValue = snoise(warpedUv * 3.0 + time * 0.1) * uNoise;

    // Create multiple color bands with different phases
    float bandWidth = 0.08;
    float totalIntensity = 0.0;
    vec3 finalColor = vec3(0.0);

    for (int i = 0; i < 8; i++) {
      if (i >= uColorCount) break;

      // Each color band has its own wave pattern
      float phase = float(i) * 1.5;
      float bandOffset = float(i) * 0.15 - 0.3;

      // Create curved band using sine waves
      float wave1 = sin(warpedUv.x * uFrequency * 2.0 + time * 0.8 + phase) * 0.3;
      float wave2 = cos(warpedUv.y * uFrequency * 1.5 + time * 0.6 + phase * 0.7) * 0.2;
      float wave3 = sin((warpedUv.x + warpedUv.y) * uFrequency * 1.2 + time + phase * 0.5) * 0.15;

      // Distance from the band center line
      float bandCenter = warpedUv.y + wave1 + wave2 + wave3 + bandOffset + noiseValue * 0.5;

      // Create smooth band with falloff
      float bandIntensity = 1.0 - smoothstep(0.0, bandWidth, abs(bandCenter));
      bandIntensity = pow(bandIntensity, 1.5); // Sharper falloff

      // Add glow around the band
      float glow = 1.0 - smoothstep(0.0, bandWidth * 3.0, abs(bandCenter));
      glow = pow(glow, 3.0) * 0.4;

      float combinedIntensity = bandIntensity + glow;

      // Accumulate color
      finalColor += uColors[i] * combinedIntensity;
      totalIntensity += combinedIntensity;
    }

    // Normalize and add subtle ambient
    if (totalIntensity > 0.0) {
      finalColor = finalColor / max(totalIntensity, 1.0);
    }

    // Dark background color
    vec3 bgColor = vec3(0.02, 0.02, 0.04);

    // Mix with background based on intensity
    float mixFactor = clamp(totalIntensity, 0.0, 1.0);
    vec3 outputColor = mix(bgColor, finalColor, mixFactor);

    // Calculate alpha
    float alpha = uTransparent ? mixFactor * 0.95 + 0.05 : 1.0;

    gl_FragColor = vec4(outputColor, alpha);
  }
`;

function hexToRgb(hex: string): THREE.Vector3 {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (result) {
    return new THREE.Vector3(
      parseInt(result[1], 16) / 255,
      parseInt(result[2], 16) / 255,
      parseInt(result[3], 16) / 255
    );
  }
  return new THREE.Vector3(0.5, 0.5, 0.5);
}

const defaultColors = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981"];

export function ColorBends({
  rotation = 45,
  autoRotate = 0,
  speed = 0.2,
  colors = defaultColors,
  transparent = true,
  scale = 1,
  frequency = 1,
  warpStrength = 1,
  mouseInfluence = 1,
  parallax = 0.5,
  noise = 0.1,
  className = "",
  style = {},
}: ColorBendsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const materialRef = useRef<THREE.ShaderMaterial | null>(null);
  const frameRef = useRef<number>(0);
  const mouseRef = useRef({ x: 0, y: 0 });
  const currentRotationRef = useRef(rotation * (Math.PI / 180));
  // eslint-disable-next-line react-hooks/purity
  const startTimeRef = useRef(Date.now());

  const colorVectors = useMemo(() => {
    const vecs: THREE.Vector3[] = [];
    for (let i = 0; i < 8; i++) {
      if (i < colors.length) {
        vecs.push(hexToRgb(colors[i]));
      } else {
        vecs.push(new THREE.Vector3(0, 0, 0));
      }
    }
    return vecs;
  }, [colors]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    mouseRef.current = {
      x: ((e.clientX - rect.left) / rect.width) * 2 - 1,
      y: -((e.clientY - rect.top) / rect.height) * 2 + 1,
    };
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;

    // Setup renderer
    const renderer = new THREE.WebGLRenderer({
      alpha: transparent,
      antialias: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Setup scene
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    // Setup camera
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 10);
    camera.position.z = 1;
    cameraRef.current = camera;

    // Setup material
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uRotation: { value: rotation * (Math.PI / 180) },
        uScale: { value: scale },
        uFrequency: { value: frequency },
        uWarpStrength: { value: warpStrength },
        uNoise: { value: noise },
        uMouse: { value: new THREE.Vector2(0, 0) },
        uMouseInfluence: { value: mouseInfluence },
        uParallax: { value: parallax },
        uColors: { value: colorVectors },
        uColorCount: { value: colors.length },
        uTransparent: { value: transparent },
      },
      transparent: transparent,
    });
    materialRef.current = material;

    // Setup geometry
    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Animation loop
    const animate = () => {
      frameRef.current = requestAnimationFrame(animate);

      const elapsed = (Date.now() - startTimeRef.current) / 1000;

      // Update auto-rotation
      if (autoRotate !== 0) {
        currentRotationRef.current += autoRotate * (Math.PI / 180) * 0.016;
      }

      // Update uniforms
      if (materialRef.current) {
        materialRef.current.uniforms.uTime.value = elapsed * speed;
        materialRef.current.uniforms.uRotation.value = currentRotationRef.current;
        materialRef.current.uniforms.uMouse.value.set(
          mouseRef.current.x,
          mouseRef.current.y
        );
      }

      renderer.render(scene, camera);
    };

    animate();

    // Handle resize
    const handleResize = () => {
      if (!container || !renderer) return;
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(frameRef.current);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [
    rotation,
    autoRotate,
    speed,
    colors,
    colorVectors,
    transparent,
    scale,
    frequency,
    warpStrength,
    mouseInfluence,
    parallax,
    noise,
    handleMouseMove,
  ]);

  // Update uniforms when props change
  useEffect(() => {
    if (materialRef.current) {
      materialRef.current.uniforms.uScale.value = scale;
      materialRef.current.uniforms.uFrequency.value = frequency;
      materialRef.current.uniforms.uWarpStrength.value = warpStrength;
      materialRef.current.uniforms.uNoise.value = noise;
      materialRef.current.uniforms.uMouseInfluence.value = mouseInfluence;
      materialRef.current.uniforms.uParallax.value = parallax;
      materialRef.current.uniforms.uColors.value = colorVectors;
      materialRef.current.uniforms.uColorCount.value = colors.length;
    }
  }, [scale, frequency, warpStrength, noise, mouseInfluence, parallax, colorVectors, colors.length]);

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 ${className}`}
      style={{ ...style }}
    />
  );
}

export default ColorBends;
