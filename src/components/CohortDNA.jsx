import React, { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import {
  ArrowRight,
  Dna,
  X,
  Activity,
  HeartPulse,
  Footprints,
  Pill,
  CalendarDays,
  Gauge,
} from 'lucide-react';

const nodes = [
  {
    key: 'age',
    label: 'AGE',
    sublabel: 'Demographics',
    description: 'Age captures the demographic structure of the source population and helps identify how cohort characteristics vary across age groups.',
    icon: CalendarDays,
  },
  {
    key: 'diabetic',
    label: 'DIABETES',
    sublabel: 'Clinical Condition',
    description: 'Diabetes represents a key clinical condition in the cohort and helps characterize disease burden and condition-specific population patterns.',
    icon: HeartPulse,
  },
  {
    key: 'bp',
    label: 'BLOOD PRESSURE',
    sublabel: 'Cardiovascular',
    description: 'Blood pressure captures cardiovascular measurements within the population and helps reveal relationships between age, disease status, and vital signs.',
    icon: Gauge,
  },
  {
    key: 'activity',
    label: 'ACTIVITY',
    sublabel: 'Lifestyle',
    description: 'Activity represents daily movement and lifestyle behavior, providing a behavioral dimension for understanding the synthetic cohort.',
    icon: Footprints,
  },
  {
    key: 'pain',
    label: 'PAIN',
    sublabel: 'Self-Reported',
    description: 'Pain captures patient-reported symptom burden and provides a subjective dimension for evaluating relationships within the cohort.',
    icon: Activity,
  },
  {
    key: 'adherence',
    label: 'ADHERENCE',
    sublabel: 'Medication',
    description: 'Medication adherence represents treatment behavior and helps characterize how consistently patients follow prescribed medication patterns.',
    icon: Pill,
  },
];

const dnaConnections = [
  { nodeIndex: 0, helixIndex: 2, side: 'left' },    // AGE
  { nodeIndex: 1, helixIndex: 6, side: 'right' },   // DIABETES
  { nodeIndex: 2, helixIndex: 10, side: 'left' },  // BP
  { nodeIndex: 3, helixIndex: 13, side: 'right' },  // ACTIVITY
  { nodeIndex: 4, helixIndex: 17, side: 'left' },  // PAIN
  { nodeIndex: 5, helixIndex: 20, side: 'right' }, // ADHERENCE
];

function cylinderBetween(a, b, radius, material) {
  const direction = new THREE.Vector3().subVectors(b, a);
  const length = direction.length();

  const geometry = new THREE.CylinderGeometry(
      radius,
      radius,
      length,
      10
  );

  const mesh = new THREE.Mesh(geometry, material);

  mesh.position.copy(a).add(b).multiplyScalar(0.5);

  mesh.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      direction.normalize()
  );

  return mesh;
}

export default function CohortDNA({ setActiveView }) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const dnaGroupRef = useRef(null);
  const connectionSvgRef = useRef(null);
  const calloutRefs = useRef([]);
  const rendererRef = useRef(null);
  const frameRef = useRef(null);

  const draggingRef = useRef(false);
  const movedRef = useRef(false);

  const pointerRef = useRef({
    x: 0,
    y: 0,
  });

  const rotationRef = useRef({
    x: 0.04,
    y: -0.15,
  });

  const [selectedNode, setSelectedNode] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const particlePositions = useMemo(() => {
    const result = [];

    for (let i = 0; i < 80; i++) {
      result.push({
        x: (Math.random() - 0.5) * 8,
        y: (Math.random() - 0.5) * 8,
        z: (Math.random() - 0.5) * 5,
      });
    }

    return result;
  }, []);

  useEffect(() => {
    const mount = mountRef.current;

    if (!mount) return;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
        42,
        mount.clientWidth / mount.clientHeight,
        0.1,
        100
    );

    camera.position.set(0, 0, 9);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });

    renderer.setPixelRatio(
        Math.min(window.devicePixelRatio, 2)
    );

    renderer.setSize(
        mount.clientWidth,
        mount.clientHeight
    );

    renderer.setClearColor(0x000000, 0);

    mount.appendChild(renderer.domElement);

    rendererRef.current = renderer;

    // Lighting
    scene.add(
        new THREE.AmbientLight(
            0xffffff,
            2.4
        )
    );

    const keyLight = new THREE.PointLight(
        0xffd7c5,
        20,
        20
    );

    keyLight.position.set(3, 4, 5);
    scene.add(keyLight);

    const warmLight = new THREE.PointLight(
        0xc68b2c,
        15,
        18
    );

    warmLight.position.set(-4, -2, 4);
    scene.add(warmLight);

    // Main DNA group
    const dnaGroup = new THREE.Group();

    dnaGroupRef.current = dnaGroup;

    scene.add(dnaGroup);

    const maroon = new THREE.MeshStandardMaterial({
      color: 0x7d2338,
      roughness: 0.3,
      metalness: 0.15,
    });

    const gold = new THREE.MeshStandardMaterial({
      color: 0xc68b2c,
      roughness: 0.28,
      metalness: 0.2,
    });

    const rungMaterial = new THREE.MeshStandardMaterial({
      color: 0xe89b72,
      roughness: 0.25,
      metalness: 0.15,
    });

    const glowingMaroon = new THREE.MeshStandardMaterial({
      color: 0x9c304d,
      emissive: 0x4a1020,
      emissiveIntensity: 0.7,
      roughness: 0.22,
    });

    const glowingGold = new THREE.MeshStandardMaterial({
      color: 0xf0b35d,
      emissive: 0x754315,
      emissiveIntensity: 0.65,
      roughness: 0.2,
    });

    const strandRadius = 0.075;
    const nodeRadius = 0.135;

    const pairs = 23;
    const height = 5.8;
    const amplitude = 0.92;
    const turns = 2.25;

    const leftPoints = [];
    const rightPoints = [];

    const connectionPoints = [];

    for (let i = 0; i < pairs; i++) {
      const t = i / (pairs - 1);

      const y = (t - 0.5) * height;

      const angle =
          t *
          Math.PI *
          2 *
          turns;

      leftPoints.push(
          new THREE.Vector3(
              Math.cos(angle) * amplitude,
              y,
              Math.sin(angle) * amplitude
          )
      );

      rightPoints.push(
          new THREE.Vector3(
              -Math.cos(angle) * amplitude,
              y,
              -Math.sin(angle) * amplitude
          )
      );
    }

    /*
     * Store the exact 3D points used by the DNA.
     * These are the positions that the SVG connection
     * lines will follow while the DNA rotates.
     */
    dnaConnections.forEach((connection) => {
      const point =
          connection.side === 'left'
              ? leftPoints[connection.helixIndex]
              : rightPoints[connection.helixIndex];

      if (point) {
        connectionPoints.push(point.clone());
      }
    });

    // Actual curved DNA strands
    const leftCurve =
        new THREE.CatmullRomCurve3(
            leftPoints
        );

    const rightCurve =
        new THREE.CatmullRomCurve3(
            rightPoints
        );

    const strandGeometry =
        new THREE.TubeGeometry(
            leftCurve,
            160,
            strandRadius,
            12,
            false
        );

    const leftStrand =
        new THREE.Mesh(
            strandGeometry,
            maroon
        );

    dnaGroup.add(leftStrand);

    const rightStrand =
        new THREE.Mesh(
            new THREE.TubeGeometry(
                rightCurve,
                160,
                strandRadius,
                12,
                false
            ),
            gold
        );

    dnaGroup.add(rightStrand);

    // Base pairs + spherical nodes
    const nodeGeometry =
        new THREE.SphereGeometry(
            nodeRadius,
            18,
            18
        );

    for (let i = 0; i < pairs; i++) {
      const left = leftPoints[i];
      const right = rightPoints[i];

      const rung = cylinderBetween(
          left,
          right,
          0.035,
          rungMaterial
      );

      dnaGroup.add(rung);

      const leftNode =
          new THREE.Mesh(
              nodeGeometry,
              i % 3 === 0
                  ? glowingMaroon
                  : maroon
          );

      const rightNode =
          new THREE.Mesh(
              nodeGeometry,
              i % 3 === 0
                  ? glowingGold
                  : gold
          );

      leftNode.position.copy(left);
      rightNode.position.copy(right);

      dnaGroup.add(leftNode);
      dnaGroup.add(rightNode);

      // Tiny inner glow on selected base pairs
      if (i % 4 === 0) {
        const glow =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.19,
                    16,
                    16
                ),
                new THREE.MeshBasicMaterial({
                  color: 0xe89b72,
                  transparent: true,
                  opacity: 0.08,
                })
            );

        glow.position.copy(left);

        dnaGroup.add(glow);
      }
    }

    // Floating particles around the helix
    const particleGeometry =
        new THREE.BufferGeometry();

    const positions =
        new Float32Array(
            particlePositions.flatMap((p) => [
              p.x,
              p.y,
              p.z,
            ])
        );

    particleGeometry.setAttribute(
        'position',
        new THREE.BufferAttribute(
            positions,
            3
        )
    );

    const particleMaterial =
        new THREE.PointsMaterial({
          color: 0xc68b2c,
          size: 0.045,
          transparent: true,
          opacity: 0.5,
        });

    const particles =
        new THREE.Points(
            particleGeometry,
            particleMaterial
        );

    dnaGroup.add(particles);

    // Initial position
    dnaGroup.position.y = 0;

    // Resize
    const handleResize = () => {
      if (!mount || !renderer) return;

      const width = mount.clientWidth;
      const height = mount.clientHeight;

      if (!width || !height) return;

      camera.aspect =
          width / height;

      camera.updateProjectionMatrix();

      renderer.setSize(
          width,
          height
      );
    };

    window.addEventListener(
        'resize',
        handleResize
    );

    /*
     * Convert a real 3D DNA position into
     * SVG coordinates and connect it to the
     * corresponding HTML callout.
     */
    const updateConnections = () => {
      if (!dnaGroupRef.current) return;

      const connectionSvg =
          connectionSvgRef.current;

      if (!connectionSvg) return;

      dnaGroup.updateMatrixWorld(true);
      camera.updateMatrixWorld(true);

      const stage =
          mount.parentElement ||
          mount;

      const stageRect =
          stage.getBoundingClientRect();

      if (
          !stageRect.width ||
          !stageRect.height
      ) {
        return;
      }

      connectionPoints.forEach(
          (point, index) => {
            const connection =
                dnaConnections[index];

            const refs =
                calloutRefs.current[index];

            if (
                !refs?.path ||
                !refs?.node ||
                !refs?.halo
            ) {
              return;
            }

            if (!refs?.element) {
              return;
            }

            /*
             * Clone because localToWorld mutates
             * the vector.
             */
            const worldPoint =
                point.clone();

            dnaGroup.localToWorld(
                worldPoint
            );

            /*
             * Project the 3D point into normalized
             * device coordinates.
             */
            worldPoint.project(camera);

            /*
             * Convert the projected point into
             * the SVG's 1000 x 560 coordinate system.
             */
            const x =
                ((worldPoint.x + 1) / 2) *
                1000;

            const y =
                ((1 - worldPoint.y) / 2) *
                560;

            /*
             * Find the actual position of the
             * HTML callout.
             */
            const rect =
                refs.element.getBoundingClientRect();

            const targetX =
                connection.side === 'left'
                    ? ((rect.right -
                            stageRect.left) /
                        stageRect.width) *
                    1000
                    : ((rect.left -
                            stageRect.left) /
                        stageRect.width) *
                    1000;

            const targetY =
                ((rect.top +
                        rect.height / 2 -
                        stageRect.top) /
                    stageRect.height) *
                560;

            /*
             * Curve the line outward from the DNA.
             */
            const controlOffset =
                connection.side === 'left'
                    ? 70
                    : -70;

            const path = `
            M ${x} ${y}
            C ${x + controlOffset} ${y},
              ${targetX - controlOffset} ${targetY},
              ${targetX} ${targetY}
          `;

            refs.path.setAttribute(
                'd',
                path
            );

            refs.node.setAttribute(
                'cx',
                x
            );

            refs.node.setAttribute(
                'cy',
                y
            );

            refs.halo.setAttribute(
                'cx',
                x
            );

            refs.halo.setAttribute(
                'cy',
                y
            );

            /*
             * Camera is looking from positive Z.
             * Fade the connection when the DNA point
             * rotates behind the helix.
             */
            const visible =
                worldPoint.z > -0.8;

            refs.node.style.opacity =
                visible ? '1' : '0.22';

            refs.halo.style.opacity =
                visible ? '1' : '0.08';

            refs.path.style.opacity =
                visible ? '0.8' : '0.22';
          }
      );
    };

    // Animation
    const animate = () => {
      frameRef.current =
          requestAnimationFrame(
              animate
          );

      if (!draggingRef.current) {
        rotationRef.current.y +=
            0.0015;
      }

      dnaGroup.rotation.x =
          rotationRef.current.x;

      dnaGroup.rotation.y =
          rotationRef.current.y;

      particles.rotation.y -=
          0.0005;

      updateConnections();

      renderer.render(
          scene,
          camera
      );
    };

    animate();

    return () => {
      cancelAnimationFrame(
          frameRef.current
      );

      window.removeEventListener(
          'resize',
          handleResize
      );

      renderer.dispose();

      if (
          mount.contains(
              renderer.domElement
          )
      ) {
        mount.removeChild(
            renderer.domElement
        );
      }

      scene.traverse(
          (object) => {
            if (object.geometry) {
              object.geometry.dispose();
            }

            if (object.material) {
              if (
                  Array.isArray(
                      object.material
                  )
              ) {
                object.material.forEach(
                    (material) =>
                        material.dispose()
                );
              } else {
                object.material.dispose();
              }
            }
          }
      );
    };
  }, [particlePositions]);

  const handlePointerDown = (
      event
  ) => {
    draggingRef.current = true;
    movedRef.current = false;

    pointerRef.current = {
      x: event.clientX,
      y: event.clientY,
    };

    setIsDragging(true);

    event.currentTarget.setPointerCapture?.(
        event.pointerId
    );
  };

  const handlePointerMove = (
      event
  ) => {
    if (!draggingRef.current) {
      return;
    }

    const dx =
        event.clientX -
        pointerRef.current.x;

    const dy =
        event.clientY -
        pointerRef.current.y;

    if (
        Math.abs(dx) > 3 ||
        Math.abs(dy) > 3
    ) {
      movedRef.current = true;
    }

    rotationRef.current.y +=
        dx * 0.008;

    rotationRef.current.x +=
        dy * 0.006;

    rotationRef.current.x =
        THREE.MathUtils.clamp(
            rotationRef.current.x,
            -0.65,
            0.65
        );

    pointerRef.current = {
      x: event.clientX,
      y: event.clientY,
    };
  };

  const handlePointerUp = (
      event
  ) => {
    draggingRef.current = false;

    setIsDragging(false);

    event.currentTarget.releasePointerCapture?.(
        event.pointerId
    );

    // A click opens the details.
    // A drag does not.
    if (!movedRef.current) {
      setShowDetails(true);
    }
  };

  const exploreDataset = () => {
    setShowDetails(false);
    setSelectedNode(null);

    setActiveView(
        'dataset-dna'
    );
  };

  return (
      <>
        <div className="cohort-dna-3d-stage">
          <div className="dna-3d-glow" />

          <div className="dna-3d-orbit orbit-one" />
          <div className="dna-3d-orbit orbit-two" />

          {/* SVG connection layer */}
          <svg
              ref={connectionSvgRef}
              className="dna-connection-layer"
              viewBox="0 0 1000 560"
              preserveAspectRatio="none"
              aria-hidden="true"
          >
            {dnaConnections.map(
                (connection, index) => (
                    <g key={index}>
                      <path
                          ref={(el) => {
                            if (
                                !calloutRefs.current[
                                    index
                                    ]
                            ) {
                              calloutRefs.current[
                                  index
                                  ] = {};
                            }

                            calloutRefs.current[
                                index
                                ].path = el;
                          }}
                          className={`dna-connection-path ${
                              connection.side ===
                              'left'
                                  ? 'connection-left'
                                  : 'connection-right'
                          }`}
                      />

                      <circle
                          ref={(el) => {
                            if (
                                !calloutRefs.current[
                                    index
                                    ]
                            ) {
                              calloutRefs.current[
                                  index
                                  ] = {};
                            }

                            calloutRefs.current[
                                index
                                ].node = el;
                          }}
                          className="dna-connection-node"
                          r="5"
                      />

                      <circle
                          ref={(el) => {
                            if (
                                !calloutRefs.current[
                                    index
                                    ]
                            ) {
                              calloutRefs.current[
                                  index
                                  ] = {};
                            }

                            calloutRefs.current[
                                index
                                ].halo = el;
                          }}
                          className="dna-connection-halo"
                          r="13"
                      />
                    </g>
                )
            )}
          </svg>

          {/* Three.js DNA canvas */}
          <div
              ref={mountRef}
              className={`dna-3d-canvas ${
                  isDragging
                      ? 'dna-is-dragging'
                      : ''
              }`}
              onPointerDown={
                handlePointerDown
              }
              onPointerMove={
                handlePointerMove
              }
              onPointerUp={
                handlePointerUp
              }
              onPointerCancel={
                handlePointerUp
              }
          />

          {/* Clinical callouts */}
          {nodes.map(
              (node, index) => {
                const Icon =
                    node.icon;

                return (
                    <button
                        key={node.key}
                        ref={(el) => {
                          calloutRefs.current[
                              index
                              ] = {
                            ...(
                                calloutRefs.current[
                                    index
                                    ] || {}
                            ),
                            element: el,
                          };
                        }}
                        type="button"
                        className={`dna-3d-callout callout-${index}`}
                        onClick={() => {
                          setSelectedNode(
                              node
                          );

                          setShowDetails(
                              true
                          );
                        }}
                    >
                <span className="dna-3d-callout-icon">
                  <Icon size={16} />
                </span>

                      <span>
                  <strong>
                    {node.label}
                  </strong>

                  <small>
                    {node.sublabel}
                  </small>
                </span>
                    </button>
                );
              }
          )}

          <div className="dna-3d-instruction">
          <span>
            6 CLINICAL DIMENSIONS
          </span>

            <i />

            <span>
            DRAG TO ROTATE
          </span>

            <ArrowRight size={14} />
          </div>
        </div>

        {/* Detail modal */}
        {showDetails && (
            <div
                className="cohort-dna-modal-backdrop"
                onClick={() =>
                    setShowDetails(false)
                }
            >
              <div
                  className="cohort-dna-modal"
                  onClick={(event) =>
                      event.stopPropagation()
                  }
              >
                <button
                    type="button"
                    className="cohort-dna-close"
                    onClick={() =>
                        setShowDetails(false)
                    }
                    aria-label="Close"
                >
                  <X size={18} />
                </button>

                <div className="flex items-center gap-3 mb-5">
                  <div className="w-11 h-11 rounded-xl bg-[#6B1D2F] text-white flex items-center justify-center">
                    <Dna size={22} />
                  </div>

                  <div>
                    <p className="text-[10px] font-bold tracking-[0.18em] text-[#6B1D2F]">
                      SYNORA INTELLIGENCE
                    </p>

                    <h3 className="font-serif text-2xl font-bold text-[var(--color-cocoa-text)]">
                      {selectedNode?.label ||
                          'Cohort DNA'}
                    </h3>
                  </div>
                </div>

                {selectedNode ? (
                    <div className="mb-6 rounded-2xl bg-[var(--color-cream-surface)] border border-[var(--color-border-subtle)] p-5">
                      <p className="text-sm font-semibold text-[var(--color-cocoa-text)] mb-1">
                        {
                          selectedNode.sublabel
                        }
                      </p>

                      <p className="text-sm leading-relaxed text-[var(--color-cocoa-subtext)]">
                        {selectedNode?.description}
                      </p>
                    </div>
                ) : (
                    <p className="text-sm leading-relaxed text-[var(--color-cocoa-subtext)] mb-6">
                      Cohort DNA is a
                      visual fingerprint
                      of the source
                      population. It
                      organizes the
                      clinical dimensions
                      used throughout
                      dataset
                      intelligence, cohort
                      design, feasibility
                      analysis, generation,
                      and validation.
                    </p>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-6">
                  {nodes.map(
                      (node) => (
                          <button
                              key={node.key}
                              type="button"
                              onClick={() =>
                                  setSelectedNode(
                                      node
                                  )
                              }
                              className={`text-left p-3 rounded-xl border transition-all ${
                                  selectedNode?.key ===
                                  node.key
                                      ? 'border-[#6B1D2F] bg-[#6B1D2F]/10'
                                      : 'border-[var(--color-border-subtle)] bg-[var(--color-card-white)] hover:border-[#6B1D2F]/40'
                              }`}
                          >
                    <span className="text-[10px] font-bold tracking-wide text-[var(--color-cocoa-text)]">
                      {node.label}
                    </span>
                          </button>
                      )
                  )}
                </div>

                <button
                    type="button"
                    onClick={
                      exploreDataset
                    }
                    className="w-full px-5 py-3.5 bg-[#6B1D2F] hover:bg-[#8B263E] text-white text-sm font-bold rounded-xl transition-all flex items-center justify-center gap-2"
                >
              <span>
                Explore Dataset DNA
              </span>

                  <ArrowRight
                      size={16}
                  />
                </button>
              </div>
            </div>
        )}
      </>
  );
}