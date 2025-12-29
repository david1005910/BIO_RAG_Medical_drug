/**
 * 3D 벡터 공간 시각화 컴포넌트
 * 검색어와 의약품들의 유사도 관계를 3D 공간에서 애니메이션으로 표시
 */

import { useRef, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, Text, Line } from '@react-three/drei'
import * as THREE from 'three'

interface VectorPoint {
  id: string
  name: string
  x: number
  y: number
  z: number
  similarity: number
  similarity_level: number
  color: string
}

interface VectorSpace3DProps {
  queryPoint: VectorPoint
  drugPoints: VectorPoint[]
  similarityLevels: { level: number; label: string; range: string; color: string }[]
  onPointClick?: (point: VectorPoint) => void
}

// 개별 포인트 (구체) 컴포넌트
function DataPoint({
  point,
  isQuery = false,
  onClick,
}: {
  point: VectorPoint
  isQuery?: boolean
  onClick?: () => void
}) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  // 애니메이션: 부드럽게 회전 및 펄스
  useFrame(() => {
    if (meshRef.current) {
      // 쿼리 포인트는 회전
      if (isQuery) {
        meshRef.current.rotation.y += 0.01
      }
      // 호버 시 스케일 애니메이션
      const scale = hovered ? 1.3 : 1.0
      meshRef.current.scale.lerp(new THREE.Vector3(scale, scale, scale), 0.1)
    }
  })

  const size = isQuery ? 0.3 : 0.15 + point.similarity * 0.15

  return (
    <group position={[point.x, point.y, point.z]}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {isQuery ? (
          <octahedronGeometry args={[size, 0]} />
        ) : (
          <sphereGeometry args={[size, 16, 16]} />
        )}
        <meshStandardMaterial
          color={point.color}
          emissive={point.color}
          emissiveIntensity={hovered ? 0.5 : 0.2}
          transparent
          opacity={isQuery ? 1 : 0.8}
        />
      </mesh>
      {/* 호버 시 라벨 표시 */}
      {hovered && (
        <Text
          position={[0, size + 0.3, 0]}
          fontSize={0.2}
          color="white"
          anchorX="center"
          anchorY="bottom"
          outlineWidth={0.02}
          outlineColor="#000000"
        >
          {point.name.length > 15 ? point.name.slice(0, 15) + '...' : point.name}
          {'\n'}
          {isQuery ? '검색어' : `유사도: ${(point.similarity * 100).toFixed(1)}%`}
        </Text>
      )}
    </group>
  )
}

// 쿼리와 의약품 사이의 연결선
function ConnectionLine({
  start,
  end,
  color,
  opacity = 0.3,
}: {
  start: [number, number, number]
  end: [number, number, number]
  color: string
  opacity?: number
}) {
  return (
    <Line
      points={[start, end]}
      color={color}
      lineWidth={1}
      transparent
      opacity={opacity}
    />
  )
}

// 유사도 레벨별 구형 셸 (거리 표시)
function SimilarityShell({
  radius,
  color,
  opacity = 0.05,
}: {
  radius: number
  color: string
  opacity?: number
}) {
  return (
    <mesh>
      <sphereGeometry args={[radius, 32, 32]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        side={THREE.DoubleSide}
        wireframe
      />
    </mesh>
  )
}

// 회전하는 그리드/축
function RotatingGrid() {
  const gridRef = useRef<THREE.Group>(null)

  useFrame(() => {
    if (gridRef.current) {
      gridRef.current.rotation.y += 0.001
    }
  })

  return (
    <group ref={gridRef}>
      {/* X축 */}
      <Line points={[[-6, 0, 0], [6, 0, 0]]} color="#ef4444" lineWidth={1} opacity={0.3} transparent />
      {/* Y축 */}
      <Line points={[[0, -6, 0], [0, 6, 0]]} color="#22c55e" lineWidth={1} opacity={0.3} transparent />
      {/* Z축 */}
      <Line points={[[0, 0, -6], [0, 0, 6]]} color="#3b82f6" lineWidth={1} opacity={0.3} transparent />
    </group>
  )
}

// 메인 씬 컴포넌트
function Scene({
  queryPoint,
  drugPoints,
  onPointClick,
}: {
  queryPoint: VectorPoint
  drugPoints: VectorPoint[]
  onPointClick?: (point: VectorPoint) => void
}) {
  // 유사도 레벨별 반경 (1~5)
  const shellRadii = [1.0, 2.0, 3.0, 4.0, 5.0]
  const shellColors = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444']

  return (
    <>
      {/* 조명 */}
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} />

      {/* 배경 그리드 */}
      <RotatingGrid />

      {/* 유사도 레벨 셸 */}
      {shellRadii.map((radius, i) => (
        <SimilarityShell
          key={i}
          radius={radius}
          color={shellColors[i]}
          opacity={0.03}
        />
      ))}

      {/* 연결선 */}
      {drugPoints.map((point) => (
        <ConnectionLine
          key={`line-${point.id}`}
          start={[queryPoint.x, queryPoint.y, queryPoint.z]}
          end={[point.x, point.y, point.z]}
          color={point.color}
          opacity={0.2 + point.similarity * 0.3}
        />
      ))}

      {/* 의약품 포인트들 */}
      {drugPoints.map((point) => (
        <DataPoint
          key={point.id}
          point={point}
          onClick={() => onPointClick?.(point)}
        />
      ))}

      {/* 쿼리 포인트 (중심) */}
      <DataPoint point={queryPoint} isQuery onClick={() => onPointClick?.(queryPoint)} />

      {/* 카메라 컨트롤 */}
      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        autoRotate
        autoRotateSpeed={0.5}
        minDistance={3}
        maxDistance={20}
      />
    </>
  )
}

// 범례 컴포넌트
function Legend({
  levels,
}: {
  levels: { level: number; label: string; range: string; color: string }[]
}) {
  return (
    <div className="absolute bottom-4 left-4 glass-card p-4 space-y-2">
      <h4 className="text-sm font-bold text-white mb-2">유사도 레벨</h4>
      {levels.map((level) => (
        <div key={level.level} className="flex items-center gap-2 text-xs">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: level.color }}
          />
          <span className="text-glass-muted">
            {level.label}: {level.range}
          </span>
        </div>
      ))}
      <div className="flex items-center gap-2 text-xs mt-2 pt-2 border-t border-white/10">
        <div className="w-3 h-3 bg-purple-500 rotate-45" />
        <span className="text-glass-muted">검색어 (중심)</span>
      </div>
    </div>
  )
}

// 선택된 포인트 정보 패널
function SelectedPointInfo({ point }: { point: VectorPoint | null }) {
  if (!point) return null

  return (
    <div className="absolute top-4 right-4 glass-card p-4 max-w-xs">
      <h4 className="text-sm font-bold text-white mb-2">{point.name}</h4>
      <div className="space-y-1 text-xs text-glass-muted">
        <p>유사도: {(point.similarity * 100).toFixed(1)}%</p>
        <p>
          레벨: {point.similarity_level === 0 ? '검색어' : `${point.similarity_level}단계`}
        </p>
        <p>
          위치: ({point.x.toFixed(2)}, {point.y.toFixed(2)}, {point.z.toFixed(2)})
        </p>
      </div>
    </div>
  )
}

// 메인 컴포넌트
export default function VectorSpace3D({
  queryPoint,
  drugPoints,
  similarityLevels,
  onPointClick,
}: VectorSpace3DProps) {
  const [selectedPoint, setSelectedPoint] = useState<VectorPoint | null>(null)

  const handlePointClick = (point: VectorPoint) => {
    setSelectedPoint(point)
    onPointClick?.(point)
  }

  return (
    <div className="relative w-full h-[600px] glass-panel rounded-2xl overflow-hidden">
      <Canvas
        camera={{ position: [8, 5, 8], fov: 60 }}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
      >
        <Scene
          queryPoint={queryPoint}
          drugPoints={drugPoints}
          onPointClick={handlePointClick}
        />
      </Canvas>

      {/* 범례 */}
      <Legend levels={similarityLevels} />

      {/* 선택된 포인트 정보 */}
      <SelectedPointInfo point={selectedPoint} />

      {/* 조작 안내 */}
      <div className="absolute bottom-4 right-4 text-xs text-glass-muted">
        <p>마우스 드래그: 회전</p>
        <p>스크롤: 확대/축소</p>
        <p>클릭: 정보 보기</p>
      </div>
    </div>
  )
}
