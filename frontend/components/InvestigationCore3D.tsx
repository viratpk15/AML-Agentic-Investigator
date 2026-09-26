"use client";

import React, { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { EngineState } from "@/types";

interface CoreSceneProps {
  state: EngineState;
}

function PulsingCore({ state }: { state: EngineState }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const innerRef = useRef<THREE.Mesh>(null!);
  const ringRef1 = useRef<THREE.Mesh>(null!);
  const ringRef2 = useRef<THREE.Mesh>(null!);
  const ringRef3 = useRef<THREE.Mesh>(null!);

  const colorConfig = useMemo(() => {
    switch (state) {
      case "ANALYZING":
        return { primary: "#06b6d4", emissive: "#0891b2", speed: 2.5 };
      case "TOOL_EXECUTION":
        return { primary: "#f59e0b", emissive: "#d97706", speed: 3.0 };
      case "RAG_RETRIEVAL":
        return { primary: "#3b82f6", emissive: "#1d4ed8", speed: 2.2 };
      case "CRITIC":
      case "REVISION":
        return { primary: "#a855f7", emissive: "#7e22ce", speed: 2.8 };
      case "COMPLETE":
        return { primary: "#10b981", emissive: "#059669", speed: 1.0 };
      case "ERROR":
        return { primary: "#ef4444", emissive: "#b91c1c", speed: 1.0 };
      case "IDLE":
      default:
        return { primary: "#22d3ee", emissive: "#0e7490", speed: 1.2 };
    }
  }, [state]);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.4 * colorConfig.speed;
      meshRef.current.rotation.x += delta * 0.2 * colorConfig.speed;
    }
    if (innerRef.current) {
      innerRef.current.rotation.y -= delta * 0.6 * colorConfig.speed;
    }
    if (ringRef1.current) {
      ringRef1.current.rotation.x += delta * 0.8 * colorConfig.speed;
      ringRef1.current.rotation.y += delta * 0.5 * colorConfig.speed;
    }
    if (ringRef2.current) {
      ringRef2.current.rotation.y -= delta * 0.7 * colorConfig.speed;
      ringRef2.current.rotation.z += delta * 0.6 * colorConfig.speed;
    }
    if (ringRef3.current) {
      ringRef3.current.rotation.x -= delta * 0.5 * colorConfig.speed;
      ringRef3.current.rotation.z -= delta * 0.9 * colorConfig.speed;
    }
  });

  return (
    <group>
      {/* Central nucleus */}
      <mesh ref={innerRef}>
        <sphereGeometry args={[0.7, 32, 32]} />
        <meshStandardMaterial
          color={colorConfig.primary}
          emissive={colorConfig.emissive}
          emissiveIntensity={2.5}
          roughness={0.1}
          metalness={0.8}
        />
      </mesh>

      {/* Outer wireframe shell */}
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[1.2, 2]} />
        <meshStandardMaterial
          color={colorConfig.primary}
          emissive={colorConfig.emissive}
          emissiveIntensity={1.2}
          wireframe
          transparent
          opacity={0.7}
        />
      </mesh>

      {/* Orbiting Orbital Rings */}
      <mesh ref={ringRef1}>
        <torusGeometry args={[1.7, 0.02, 16, 100]} />
        <meshStandardMaterial color={colorConfig.primary} emissive={colorConfig.primary} emissiveIntensity={1.5} />
      </mesh>
      <mesh ref={ringRef2}>
        <torusGeometry args={[2.1, 0.015, 16, 100]} />
        <meshStandardMaterial color="#8b5cf6" emissive="#8b5cf6" emissiveIntensity={1.5} />
      </mesh>
      <mesh ref={ringRef3}>
        <torusGeometry args={[2.5, 0.01, 16, 100]} />
        <meshStandardMaterial color="#06b6d4" emissive="#06b6d4" emissiveIntensity={1.2} />
      </mesh>
    </group>
  );
}

function ParticleField({ state }: { state: EngineState }) {
  const count = 150;
  const points = useMemo(() => {
    const coords = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const r = 2.5 + Math.random() * 2.0;

      coords[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      coords[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      coords[i * 3 + 2] = r * Math.cos(phi);
    }
    return coords;
  }, []);

  const pointsRef = useRef<THREE.Points>(null!);

  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.15;
      pointsRef.current.rotation.x += delta * 0.08;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={count}
          array={points}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        color={state === "CRITIC" ? "#a855f7" : "#38bdf8"}
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

export default function InvestigationCore3D({ state = "IDLE" }: { state?: EngineState }) {
  return (
    <div className="relative w-full h-[320px] md:h-[400px] rounded-2xl overflow-hidden bg-gradient-to-b from-[#0b0f19] via-[#050914] to-[#030712] border border-cyan-500/20 shadow-glow">
      {/* Background radial glow */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(6,182,212,0.15)_0%,transparent_70%)]" />

      {/* HUD status label overlay */}
      <div className="absolute top-4 left-4 z-10 flex items-center space-x-2 bg-black/40 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
        <span
          className={`w-2.5 h-2.5 rounded-full ${
            state === "ANALYZING" || state === "TOOL_EXECUTION"
              ? "bg-amber-400 animate-ping"
              : state === "CRITIC"
              ? "bg-purple-400 animate-pulse"
              : state === "COMPLETE"
              ? "bg-emerald-400"
              : "bg-cyan-400"
          }`}
        />
        <span className="text-xs font-mono tracking-wider uppercase text-cyan-300">
          CORE // {state}
        </span>
      </div>

      <div className="absolute bottom-4 right-4 z-10 text-[10px] font-mono text-gray-400 uppercase tracking-widest bg-black/40 px-2.5 py-1 rounded border border-white/5">
        ORCHESTRATOR ACTIVE
      </div>

      <Canvas camera={{ position: [0, 0, 5.5], fov: 45 }}>
        <ambientLight intensity={0.6} />
        <pointLight position={[10, 10, 10]} intensity={1.5} color="#38bdf8" />
        <pointLight position={[-10, -10, -10]} intensity={1.0} color="#818cf8" />
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <PulsingCore state={state} />
          <ParticleField state={state} />
        </Float>
        <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}
