/**
 * Web3D可视化器
 * 基于Three.js实现SHP道路数据的3D可视化
 */

// 导入Three.js和OrbitControls
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';

class Web3DViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        console.log('Container ID:', containerId);
        console.log('Container element found:', this.container);
        
        if (!this.container) {
            console.error('Container element not found with ID:', containerId);
            return;
        }
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.roadLines = [];
        this.roadGroup = null;
        this.meshGroup = null;
        this.gridHelper = null;
        this.axesHelper = null;
        this.currentData = null;
        this.objLoader = new OBJLoader();
        
        // 地理坐标系原点（用于坐标转换）
        this.originLat = null;
        this.originLon = null;
        
        // 坐标偏移量（用于显示真实坐标）
        this.coordinateOffset = { x: 0.0, y: 0.0 };
        
        // 键盘控制状态
        this.keys = {
            w: false,
            a: false,
            s: false,
            d: false,
            q: false,
            e: false
        };
        
        // 鼠标控制状态
        this.mouse = {
            rightButton: false,
            lastX: 0,
            lastY: 0
        };
        
        // 线条选择状态
        this.selectedLine = null;
        this.hoveredLine = null;
        this.raycaster = new THREE.Raycaster();
        this.mouseVector = new THREE.Vector2();
        
        // 设置参数
        this.settings = {
            showGrid: true,
            showAxes: true,
            lineWidth: 2,
            lineColor: 0x000000,
            moveSpeed: 10 // 移动速度
        };
        
        this.init();
    }
    
    init() {
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createControls();
        this.createLights();
        this.createHelpers();
        this.bindEvents();
        this.animate();
        

        
        console.log('Web3D可视化器初始化完成');
    }
    

    
    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf2f2f7);
        this.scene.fog = new THREE.Fog(0xf2f2f7, 1000, 10000);
    }
    
    createCamera() {
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(75, aspect, 0.1, 10000);
        this.camera.position.set(0, 500, 1000);
        this.camera.lookAt(0, 0, 0);
    }
    
    createRenderer() {
        this.renderer = new THREE.WebGLRenderer({ 
            antialias: true,
            alpha: true
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        
        console.log('Adding renderer DOM element to container...');
        console.log('Renderer DOM element:', this.renderer.domElement);
        console.log('Container before appendChild:', this.container);
        
        this.container.appendChild(this.renderer.domElement);
        
        console.log('Renderer DOM element added successfully');
        console.log('Container children count:', this.container.children.length);
        console.log('Canvas element in DOM:', document.querySelector('#viewer canvas'));
    }
    
    createControls() {
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 10;
        this.controls.maxDistance = 5000;
        this.controls.maxPolarAngle = Math.PI / 2;
        
        // 交换鼠标按键功能：左键移动，右键旋转
        this.controls.mouseButtons = {
            LEFT: THREE.MOUSE.PAN,    // 左键设置为移动
            MIDDLE: THREE.MOUSE.DOLLY, // 中键缩放
            RIGHT: THREE.MOUSE.ROTATE  // 右键设置为旋转
        };
        
        // 绑定控制器事件
        this.controls.addEventListener('change', () => {
            // 控制器变化时不更新坐标显示，只在鼠标移动时更新
        });
    }
    
    createLights() {
        // 环境光
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        this.scene.add(ambientLight);
        
        // 方向光
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(1000, 1000, 500);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        directionalLight.shadow.camera.near = 0.5;
        directionalLight.shadow.camera.far = 5000;
        directionalLight.shadow.camera.left = -1000;
        directionalLight.shadow.camera.right = 1000;
        directionalLight.shadow.camera.top = 1000;
        directionalLight.shadow.camera.bottom = -1000;
        this.scene.add(directionalLight);
        
        // 点光源
        const pointLight = new THREE.PointLight(0x4fc3f7, 0.5, 2000);
        pointLight.position.set(0, 800, 0);
        this.scene.add(pointLight);
    }
    
    createHelpers() {
        // 网格辅助线
        this.gridHelper = new THREE.GridHelper(2000, 50, 0xc7c7cc, 0xd1d1d6);
        this.gridHelper.visible = this.settings.showGrid;
        this.scene.add(this.gridHelper);
        
        // 坐标轴辅助线
        this.axesHelper = new THREE.AxesHelper(500);
        this.axesHelper.visible = this.settings.showAxes;
        this.scene.add(this.axesHelper);
    }
    
    bindEvents() {
        console.log('Binding events...');
        console.log('Renderer DOM element:', this.renderer.domElement);
        console.log('Container element:', this.container);
        
        // 窗口大小调整
        window.addEventListener('resize', () => {
            this.onWindowResize();
        });
        
        // 鼠标事件 - 使用捕获阶段确保在OrbitControls之前处理
        this.renderer.domElement.addEventListener('mousedown', (event) => {
            console.log('Mouse down event bound');
            // 如果是左键，先处理选择逻辑，然后阻止事件传播给OrbitControls
            if (event.button === 0) {
                const rect = this.renderer.domElement.getBoundingClientRect();
                const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                this.selectLine(x, y);
                
                // 如果选中了线条，阻止OrbitControls处理此事件
                if (this.selectedLine) {
                    event.stopPropagation();
                    event.preventDefault();
                    return;
                }
            }
            this.onMouseDown(event);
        }, true); // 使用捕获阶段
        
        this.renderer.domElement.addEventListener('mouseup', (event) => {
            console.log('Mouse up event bound');
            this.onMouseUp(event);
        });
        

        
        // 直接在渲染器DOM元素上添加鼠标移动事件
        this.renderer.domElement.addEventListener('mousemove', (event) => {
            console.log('Canvas mousemove triggered:', event.clientX, event.clientY);
            this.onMouseMove(event);
        });
        
        // 也在容器上添加鼠标移动事件作为备用
        this.container.addEventListener('mousemove', (event) => {
            console.log('Container mousemove triggered:', event.clientX, event.clientY);
            this.onMouseMove(event);
        });
        
        console.log('Mouse move event listeners added to canvas and container');
        
        // 禁用右键菜单
        this.renderer.domElement.addEventListener('contextmenu', (event) => {
            event.preventDefault();
        });
        
        // 键盘事件监听
        document.addEventListener('keydown', (event) => {
            this.onKeyDown(event);
            this.updateCursor(event);
        });
        
        document.addEventListener('keyup', (event) => {
            this.onKeyUp(event);
            this.updateCursor(event);
        });
        
        // 确保容器可以获得焦点
        this.container.setAttribute('tabindex', '0');
        this.container.focus();
        
        // 重置视角按钮事件
        const resetViewBtn = document.getElementById('resetViewBtn');
        if (resetViewBtn) {
            resetViewBtn.addEventListener('click', () => this.resetToTopView());
        }
    }
    
    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }
    
    onMouseDown(event) {
        if (event.button === 2) { // 右键
            this.mouse.rightButton = true;
            this.mouse.lastX = event.clientX;
            this.mouse.lastY = event.clientY;
            event.preventDefault();
        } else if (event.button === 0) { // 左键
            // 左键既可以选择线条，也可以拖拽移动
            const rect = this.renderer.domElement.getBoundingClientRect();
            const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            this.selectLine(x, y);
        }
    }
    
    onMouseUp(event) {
        if (event.button === 2) { // 右键
            this.mouse.rightButton = false;
            event.preventDefault();
        }
    }
    
    onMouseMove(event) {
        console.log('Mouse move event triggered:', event.clientX, event.clientY);
        
        // 检测鼠标悬停的线条
        this.checkHoverLine(event);
        
        // 更新鼠标坐标显示
        const rect = this.renderer.domElement.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        console.log('Normalized mouse coordinates:', x, y);
        
        // 射线检测
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera);
        
        // 检测与道路线条的交点
        if (this.roadLines && this.roadLines.length > 0) {
            const intersects = raycaster.intersectObjects(this.roadLines);
            
            if (intersects.length > 0 && intersects[0].point) {
                // 如果鼠标悬停在线条上，显示交点坐标
                const point = intersects[0].point;
                console.log('Road intersection found:', point);
                // 确保Z轴始终为0，Y轴可以变化
                this.updateCoordinateDisplay(point.x, point.y, 0);
                return;
            }
        }
        
        // 如果没有悬停在线条上，计算鼠标在地面的投影坐标
        // 修改地面平面定义：Z=0平面，法向量为(0, 0, 1)
        const groundPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
        const groundPoint = new THREE.Vector3();
        const intersectionResult = raycaster.ray.intersectPlane(groundPlane, groundPoint);
        
        if (intersectionResult && groundPoint) {
            console.log('Ground intersection found:', groundPoint);
            // 确保Z轴始终为0，Y轴可以变化
            this.updateCoordinateDisplay(groundPoint.x, groundPoint.y, 0);
        } else {
            // 如果无法计算坐标，显示鼠标屏幕坐标
            console.log('Updating coordinates with screen coordinates:', event.clientX, event.clientY, 0);
            this.updateCoordinateDisplay(event.clientX, event.clientY, 0);
        }
    }
    
    // 更新坐标显示
    setCoordinateOffset(offsetX, offsetY) {
        this.coordinateOffset.x = offsetX || 0.0;
        this.coordinateOffset.y = offsetY || 0.0;
        console.log('设置坐标偏移量:', this.coordinateOffset);
    }
    
    updateCoordinateDisplay(x, y, z) {
        // 更新右下角坐标面板
        const mouseXElement = document.querySelector('#mouseX');
        const mouseYElement = document.querySelector('#mouseY');
        const mouseZElement = document.querySelector('#mouseZ');
        
        // 更新底部状态栏坐标
        const statusXElement = document.querySelector('#statusX');
        const statusYElement = document.querySelector('#statusY');
        const statusZElement = document.querySelector('#statusZ');
        
        console.log('更新坐标显示 (局部):', { x, y, z });
        
        // 计算真实坐标（加上偏移量）
        const realX = (x !== null && x !== undefined) ? Number(x) + this.coordinateOffset.x : null;
        const realY = (y !== null && y !== undefined) ? Number(y) + this.coordinateOffset.y : null;
        const realZ = (z !== null && z !== undefined) ? Number(z) : null;
        
        console.log('真实坐标:', { realX, realY, realZ });
        
        const xValue = (realX !== null && realX !== undefined) ? realX.toFixed(2) : '--';
        const yValue = (realY !== null && realY !== undefined) ? realY.toFixed(2) : '--';
        const zValue = (realZ !== null && realZ !== undefined) ? realZ.toFixed(2) : '--';
        
        // 更新右下角坐标面板
        if (mouseXElement) {
            mouseXElement.textContent = xValue;
        }
        if (mouseYElement) {
            mouseYElement.textContent = yValue;
        }
        if (mouseZElement) {
            mouseZElement.textContent = zValue;
        }
        
        // 更新底部状态栏坐标
        if (statusXElement) {
            statusXElement.textContent = xValue;
        }
        if (statusYElement) {
            statusYElement.textContent = yValue;
        }
        if (statusZElement) {
            statusZElement.textContent = zValue;
        }
        
        console.log('坐标已更新为:', { x: xValue, y: yValue, z: zValue });
    }
    
    onKeyDown(event) {
        const key = event.key.toLowerCase();
        if (key in this.keys) {
            this.keys[key] = true;
            event.preventDefault();
        }
    }
    
    onKeyUp(event) {
        const key = event.key.toLowerCase();
        if (key in this.keys) {
            this.keys[key] = false;
            event.preventDefault();
        }
    }
    
    updateCameraMovement() {
        if (!this.camera || !this.controls) return;
        
        let moveSpeed = this.settings.moveSpeed;
        const direction = new THREE.Vector3();
        const right = new THREE.Vector3();
        
        // 获取相机的前进方向和右方向
        this.camera.getWorldDirection(direction);
        right.crossVectors(direction, this.camera.up).normalize();
        
        // 计算移动向量
        const moveVector = new THREE.Vector3();
        
        if (this.keys.w) { // 前进
            moveVector.add(direction.clone().multiplyScalar(moveSpeed));
        }
        if (this.keys.s) { // 后退
            moveVector.add(direction.clone().multiplyScalar(-moveSpeed));
        }
        if (this.keys.a) { // 左移
            moveVector.add(right.clone().multiplyScalar(-moveSpeed));
        }
        if (this.keys.d) { // 右移
            moveVector.add(right.clone().multiplyScalar(moveSpeed));
        }
        if (this.keys.q) { // 上升
            moveVector.add(this.camera.up.clone().multiplyScalar(moveSpeed));
        }
        if (this.keys.e) { // 下降
            moveVector.add(this.camera.up.clone().multiplyScalar(-moveSpeed));
        }
        
        // 应用移动
        if (moveVector.length() > 0) {
            this.camera.position.add(moveVector);
            this.controls.target.add(moveVector);
            this.controls.update();
        }
    }
    
    updateCameraCoordinates() {
        const coords = document.getElementById('coordinates');
        if (coords) {
            const pos = this.camera.position;
            coords.textContent = `坐标: (${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)})`;
        }
    }
    
    loadGeoJSON(geojson) {
        const startTime = performance.now();
        
        try {
            // 清除之前的道路线条
            this.clearRoads();
            
            if (!geojson || !geojson.features) {
                throw new Error('无效的GeoJSON数据');
            }
            
            let totalPoints = 0;
            this.roadGroup = new THREE.Group();
            
            // 检测坐标系统并设置原点（用于地理坐标系转换）
            if (geojson.features.length > 0 && geojson.features[0].geometry.coordinates.length > 0) {
                const firstCoord = geojson.features[0].geometry.coordinates[0];
                if (Math.abs(firstCoord[0]) < 180 && Math.abs(firstCoord[1]) < 90) {
                    this.originLon = firstCoord[0];
                    this.originLat = firstCoord[1];
                }
            }
            
            // 创建线条材质
            const lineMaterial = new THREE.LineBasicMaterial({
                color: this.settings.lineColor,
                linewidth: this.settings.lineWidth,
                transparent: true,
                opacity: 0.8
            });
            
            // 处理每个道路特征
            geojson.features.forEach((feature, index) => {
                if (feature.geometry.type === 'LineString') {
                    const coordinates = feature.geometry.coordinates;
                    
                    if (coordinates.length < 2) return;
                    
                    // 创建几何体
                    const geometry = new THREE.BufferGeometry();
                    const points = [];
                    
                    coordinates.forEach(coord => {
                        // 检测坐标系统并进行适当的转换
                        let x = coord[0];
                        let y = 0; // 忽略高度信息，所有道路显示在同一平面
                        let z = -coord[1]; // Y坐标作为Z轴，取负值以正确显示
                        
                        // 如果是地理坐标系（经纬度），进行缩放和偏移
                        if (this.originLon !== null && this.originLat !== null) {
                            // 计算相对偏移并放大（1度约等于111km）
                            const scale = 100000; // 放大倍数
                            x = (x - this.originLon) * scale;
                            z = -(coord[1] - this.originLat) * scale; // 重新计算z坐标
                        }
                        
                        points.push(new THREE.Vector3(x, y, z));
                        totalPoints++;
                    });
                    
                    geometry.setFromPoints(points);
                    
                    // 创建线条
                    const line = new THREE.Line(geometry, lineMaterial.clone());
                    line.userData = {
                        roadId: feature.properties.id,
                        roadType: feature.properties.road_type,
                        name: feature.properties.name
                    };
                    
                    this.roadGroup.add(line);
                    this.roadLines.push(line);
                }
            });
            
            this.scene.add(this.roadGroup);
            this.currentData = geojson;
            
            // 调整相机视角
            this.fitCameraToRoads();
            
            // 更新统计信息
            const endTime = performance.now();
            this.updateStats({
                roadCount: geojson.features.length,
                pointCount: totalPoints,
                renderTime: Math.round(endTime - startTime)
            });
            
            console.log(`成功加载 ${geojson.features.length} 条道路，${totalPoints} 个点`);
            
        } catch (error) {
            console.error('加载GeoJSON数据时出错:', error);
            this.showError('加载数据失败: ' + error.message);
        }
    }
    
    clearRoads() {
        // 清理roadGroup
        if (this.roadGroup) {
            this.scene.remove(this.roadGroup);
            // 清理roadGroup中的所有子对象
            this.roadGroup.children.forEach(child => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            });
            this.roadGroup.clear();
            this.roadGroup = null;
        }
        
        // 清理meshGroup
        if (this.meshGroup) {
            this.scene.remove(this.meshGroup);
            // 清理meshGroup中的所有子对象
            this.meshGroup.children.forEach(child => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            });
            this.meshGroup.clear();
            this.meshGroup = null;
        }
        
        // 清理roadLines数组
        this.roadLines.forEach(line => {
            if (line.geometry) line.geometry.dispose();
            if (line.material) line.material.dispose();
        });
        this.roadLines = [];
        
        // 重置地理坐标系原点
        this.originLat = null;
        this.originLon = null;
    }
    
    fitCameraToRoads() {
        if (this.roadLines.length === 0) return;
        
        // 计算所有道路的边界框
        const box = new THREE.Box3();
        this.roadLines.forEach(line => {
            box.expandByObject(line);
        });
        
        if (box.isEmpty()) return;
        
        // 计算中心点和大小
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // 计算最大维度，考虑所有轴向
        const maxDim = Math.max(size.x, size.y, size.z);
        
        // 计算合适的相机距离，确保能看到所有内容
        const distance = maxDim * 2.5; // 调整距离倍数，使视角更靠近场景
        
        // 设置相机为斜角度视图，可以更好地展示整个坐标范围
        this.camera.position.set(
            center.x + distance * 0.6,
            center.y + distance * 0.8,
            center.z + distance * 0.6
        );
        
        // 相机朝向中心点
        this.camera.lookAt(center.x, center.y, center.z);
        
        // 更新控制器目标到中心点
        this.controls.target.copy(center);
        this.controls.update();
        
        // 调整相机的视野角度以更好地适应内容
        if (this.camera.fov) {
            const fov = Math.min(75, Math.max(30, 60 * (maxDim / distance)));
            this.camera.fov = fov;
            this.camera.updateProjectionMatrix();
        }
        
        // 调整网格和坐标轴大小
        if (this.gridHelper) {
            this.scene.remove(this.gridHelper);
            this.gridHelper = new THREE.GridHelper(maxDim * 2, 50, 0xc7c7cc, 0xd1d1d6);
            this.gridHelper.visible = this.settings.showGrid;
            this.scene.add(this.gridHelper);
        }
        
        if (this.axesHelper) {
            this.scene.remove(this.axesHelper);
            this.axesHelper = new THREE.AxesHelper(maxDim * 0.3);
            this.axesHelper.visible = this.settings.showAxes;
            this.scene.add(this.axesHelper);
        }
    }
    
    // 重置视角为俯视图
    resetToTopView() {
        if (this.roadLines.length === 0) {
            console.log('没有道路数据，无法重置视角');
            return;
        }
        
        // 计算所有道路的边界框
        const box = new THREE.Box3();
        this.roadLines.forEach(line => {
            box.expandByObject(line);
        });
        
        if (box.isEmpty()) {
            console.log('边界框为空，无法重置视角');
            return;
        }
        
        // 计算中心点和大小
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // 计算最大维度，考虑所有轴向
        const maxDim = Math.max(size.x, size.y, size.z);
        
        // 计算合适的相机距离，确保能看到所有内容
        const distance = maxDim * 2.5; // 调整距离倍数，使视角更靠近场景
        
        // 设置相机为斜角度视图，可以更好地展示整个坐标范围
        this.camera.position.set(
            center.x + distance * 0.6,
            center.y + distance * 0.8,
            center.z + distance * 0.6
        );
        
        // 相机朝向中心点
        this.camera.lookAt(center.x, center.y, center.z);
        
        // 更新控制器目标到中心点
        this.controls.target.copy(center);
        this.controls.update();
        
        // 调整相机的视野角度以更好地适应内容
        if (this.camera.fov) {
            const fov = Math.min(75, Math.max(30, 60 * (maxDim / distance)));
            this.camera.fov = fov;
            this.camera.updateProjectionMatrix();
        }
        
        console.log('视角已重置为俯视图');
    }
    

    

    

    

    
    // 选择线条
    selectLine(x, y) {
        console.log('selectLine called with:', x, y);
        console.log('roadLines count:', this.roadLines.length);
        
        // x, y 已经是标准化设备坐标
        this.mouseVector.x = x;
        this.mouseVector.y = y;
        
        // 设置射线
        this.raycaster.setFromCamera(this.mouseVector, this.camera);
        
        // 检测与道路线条的交点
        const intersects = this.raycaster.intersectObjects(this.roadLines);
        console.log('intersects found:', intersects.length);
        
        // 清除之前的选择
        this.clearLineSelection();
        
        if (intersects.length > 0) {
            const selectedObject = intersects[0].object;
            this.selectedLine = selectedObject;
            
            console.log('选中线条:', selectedObject.userData);
            
            // 高亮选中的线条
            this.highlightSelectedLine(selectedObject);
            
            // 显示线条信息
            this.showLineInfo(selectedObject);
        } else {
            console.log('没有选中任何线条');
        }
    }
    
    // 清除线条选择
    clearLineSelection() {
        if (this.selectedLine) {
            // 恢复原始颜色
            this.selectedLine.material.color.setHex(this.settings.lineColor);
            this.selectedLine = null;
        }
        
        // 隐藏信息面板
        this.hideLineInfo();
    }
    
    // 高亮选中的线条
    highlightSelectedLine(line) {
        line.material.color.setHex(0xff0000); // 红色高亮
    }
    
    // 显示线条信息
    showLineInfo(line) {
        const userData = line.userData;
        let infoPanel = document.getElementById('lineInfoPanel');
        
        if (!infoPanel) {
            infoPanel = document.createElement('div');
            infoPanel.id = 'lineInfoPanel';
            infoPanel.style.position = 'absolute';
            infoPanel.style.top = '20px';
            infoPanel.style.left = '20px';
            infoPanel.style.background = 'rgba(128, 128, 128, 0.9)';
            infoPanel.style.color = 'white';
            infoPanel.style.padding = '12px';
            infoPanel.style.borderRadius = '5px';
            infoPanel.style.fontSize = '0.9rem';
            infoPanel.style.zIndex = '1002';
            infoPanel.style.maxWidth = '350px';
            infoPanel.style.lineHeight = '1.4';
            this.container.appendChild(infoPanel);
        }
        
        // 计算线条的几何信息
        const geometry = line.geometry;
        const positions = geometry.attributes.position.array;
        const pointCount = positions.length / 3;
        
        // 计算线条长度
        let totalLength = 0;
        for (let i = 0; i < pointCount - 1; i++) {
            const x1 = positions[i * 3];
            const y1 = positions[i * 3 + 1];
            const z1 = positions[i * 3 + 2];
            const x2 = positions[(i + 1) * 3];
            const y2 = positions[(i + 1) * 3 + 1];
            const z2 = positions[(i + 1) * 3 + 2];
            
            const dx = x2 - x1;
            const dy = y2 - y1;
            const dz = z2 - z1;
            totalLength += Math.sqrt(dx * dx + dy * dy + dz * dz);
        }
        
        // 获取起始和结束坐标（局部坐标）
        const localStartX = positions[0];
        const localStartY = positions[1];
        const localStartZ = positions[2];
        const localEndX = positions[(pointCount - 1) * 3];
        const localEndY = positions[(pointCount - 1) * 3 + 1];
        const localEndZ = positions[(pointCount - 1) * 3 + 2];
        
        // 转换为真实坐标
        const startX = localStartX + this.coordinateOffset.x;
        const startY = localStartY + this.coordinateOffset.y;
        const startZ = localStartZ;
        const endX = localEndX + this.coordinateOffset.x;
        const endY = localEndY + this.coordinateOffset.y;
        const endZ = localEndZ;
        
        // 计算边界框（局部坐标）
        let localMinX = Infinity, localMaxX = -Infinity;
        let localMinY = Infinity, localMaxY = -Infinity;
        let localMinZ = Infinity, localMaxZ = -Infinity;
        
        for (let i = 0; i < pointCount; i++) {
            const x = positions[i * 3];
            const y = positions[i * 3 + 1];
            const z = positions[i * 3 + 2];
            
            localMinX = Math.min(localMinX, x);
            localMaxX = Math.max(localMaxX, x);
            localMinY = Math.min(localMinY, y);
            localMaxY = Math.max(localMaxY, y);
            localMinZ = Math.min(localMinZ, z);
            localMaxZ = Math.max(localMaxZ, z);
        }
        
        // 转换边界框为真实坐标
        const minX = localMinX + this.coordinateOffset.x;
        const maxX = localMaxX + this.coordinateOffset.x;
        const minY = localMinY + this.coordinateOffset.y;
        const maxY = localMaxY + this.coordinateOffset.y;
        const minZ = localMinZ;
        const maxZ = localMaxZ;
        
        infoPanel.innerHTML = `
            <h4 style="margin: 0 0 10px 0; color: white; font-size: 1.2rem; border-bottom: 1px solid #999; padding-bottom: 5px;">线条信息</h4>
            
            <div style="margin-bottom: 8px;"><strong>基本信息</strong></div>
            <div style="margin-left: 10px; margin-bottom: 8px;"><strong>道路ID:</strong> ${userData.roadId || 'N/A'}</div>
            
            <div style="margin-bottom: 8px;"><strong>几何信息</strong></div>
            <div style="margin-left: 10px; margin-bottom: 4px;"><strong>线条长度:</strong> ${totalLength.toFixed(2)} 米</div>
            <div style="margin-left: 10px; margin-bottom: 8px;"><strong>坐标点数:</strong> ${pointCount} 个</div>
            
            <div style="margin-bottom: 8px;"><strong>坐标范围</strong></div>
            <div style="margin-left: 10px; margin-bottom: 4px;"><strong>起始点:</strong> (${startX.toFixed(2)}, ${startY.toFixed(2)})</div>
            <div style="margin-left: 10px; margin-bottom: 4px;"><strong>结束点:</strong> (${endX.toFixed(2)}, ${endY.toFixed(2)})</div>
            <div style="margin-left: 10px; margin-bottom: 4px;"><strong>X范围:</strong> ${minX.toFixed(2)} ~ ${maxX.toFixed(2)}</div>
            <div style="margin-left: 10px; margin-bottom: 8px;"><strong>Y范围:</strong> ${minY.toFixed(2)} ~ ${maxY.toFixed(2)}</div>
            
            <div style="margin-top: 10px; font-size: 0.8rem; color: #ccc; border-top: 1px solid #666; padding-top: 5px;">点击其他地方取消选择</div>
        `;
        
        infoPanel.style.display = 'block';
    }
    
    // 隐藏线条信息
    hideLineInfo() {
        const infoPanel = document.getElementById('lineInfoPanel');
        if (infoPanel) {
            infoPanel.style.display = 'none';
        }
    }
    
    // 检测鼠标悬停的线条
    checkHoverLine(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouseVector.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouseVector.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        
        this.raycaster.setFromCamera(this.mouseVector, this.camera);
        const intersects = this.raycaster.intersectObjects(this.roadLines);
        
        // 清除之前的悬停状态
        if (this.hoveredLine && this.hoveredLine !== this.selectedLine) {
            this.hoveredLine.material.color.setHex(this.settings.lineColor);
        }
        
        if (intersects.length > 0) {
            const hoveredObject = intersects[0].object;
            
            // 只有当不是已选中的线条时才应用悬停效果
            if (hoveredObject !== this.selectedLine) {
                this.hoveredLine = hoveredObject;
                this.hoveredLine.material.color.setHex(0x007aff); // 蓝色悬停
                this.renderer.domElement.style.cursor = 'pointer';
            } else {
                this.hoveredLine = null;
                this.renderer.domElement.style.cursor = 'pointer';
            }
        } else {
            this.hoveredLine = null;
            this.renderer.domElement.style.cursor = 'default';
        }
    }
    
    // 更新光标样式
    updateCursor(event) {
        this.renderer.domElement.style.cursor = 'default';
    }
    

    
    updateStats(stats) {
        const elements = {
            roadCount: document.getElementById('roadCount'),
            pointCount: document.getElementById('pointCount'),
            renderTime: document.getElementById('renderTime')
        };
        
        if (elements.roadCount) elements.roadCount.textContent = stats.roadCount;
        if (elements.pointCount) elements.pointCount.textContent = stats.pointCount;
        if (elements.renderTime) elements.renderTime.textContent = stats.renderTime + 'ms';
    }
    
    showError(message) {
        const errorDiv = document.getElementById('error');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }
    }
    
    // 设置方法
    setShowGrid(show) {
        this.settings.showGrid = show;
        if (this.gridHelper) {
            this.gridHelper.visible = show;
        }
    }
    
    setShowAxes(show) {
        this.settings.showAxes = show;
        if (this.axesHelper) {
            this.axesHelper.visible = show;
        }
    }
    
    setLineWidth(width) {
        this.settings.lineWidth = width;
        this.roadLines.forEach(line => {
            line.material.linewidth = width;
        });
    }
    
    setLineColor(color) {
        this.settings.lineColor = color;
        this.roadLines.forEach(line => {
            line.material.color.setHex(color);
        });
    }
    
    resetView() {
        if (this.roadLines.length > 0) {
            this.fitCameraToRoads();
        } else {
            this.camera.position.set(0, 500, 1000);
            this.camera.lookAt(0, 0, 0);
            this.controls.target.set(0, 0, 0);
            this.controls.update();
        }
    }
    
    exportScene() {
        if (!this.currentData) {
            this.showError('没有可导出的数据');
            return;
        }
        
        // 导出当前场景的截图
        this.renderer.render(this.scene, this.camera);
        const canvas = this.renderer.domElement;
        const link = document.createElement('a');
        link.download = 'road_visualization.png';
        link.href = canvas.toDataURL();
        link.click();
    }
    
    animate() {
        requestAnimationFrame(() => this.animate());
        
        // 更新键盘控制的相机移动
        this.updateCameraMovement();
        
        if (this.controls) {
            this.controls.update();
        }
        
        this.renderer.render(this.scene, this.camera);
    }
    
    loadOBJ(file) {
        const startTime = performance.now();
        
        try {
            // 清除之前的模型
            this.clearRoads();
            
            this.meshGroup = new THREE.Group();
            
            // 创建文件读取器
            const reader = new FileReader();
            reader.onload = (event) => {
                const objData = event.target.result;
                
                // 使用OBJLoader加载模型
                const object = this.objLoader.parse(objData);
                
                // 创建材质
                const material = new THREE.MeshLambertMaterial({
                    color: 0x666666,
                    transparent: true,
                    opacity: 0.8
                });
                
                // 遍历加载的对象，应用材质
                object.traverse((child) => {
                    if (child.isMesh) {
                        child.material = material;
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });
                
                this.meshGroup.add(object);
                this.scene.add(this.meshGroup);
                
                // 调整相机视角
                this.fitCameraToObject(object);
                
                // 更新统计信息
                const endTime = performance.now();
                let meshCount = 0;
                let vertexCount = 0;
                
                object.traverse((child) => {
                    if (child.isMesh) {
                        meshCount++;
                        if (child.geometry && child.geometry.attributes.position) {
                            vertexCount += child.geometry.attributes.position.count;
                        }
                    }
                });
                
                this.updateStats({
                    roadCount: meshCount,
                    pointCount: vertexCount,
                    renderTime: Math.round(endTime - startTime)
                });
                
                console.log(`成功加载OBJ模型，${meshCount} 个网格，${vertexCount} 个顶点`);
            };
            
            reader.onerror = (error) => {
                console.error('读取OBJ文件时出错:', error);
                this.showError('读取OBJ文件失败');
            };
            
            reader.readAsText(file);
            
        } catch (error) {
            console.error('加载OBJ文件时出错:', error);
            this.showError('加载OBJ文件失败: ' + error.message);
        }
    }
    
    fitCameraToObject(object) {
        // 计算对象的边界框
        const box = new THREE.Box3().setFromObject(object);
        
        if (box.isEmpty()) return;
        
        // 计算中心点和大小
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        // 计算最大维度
        const maxDim = Math.max(size.x, size.y, size.z);
        
        // 计算合适的相机距离
        const distance = maxDim * 2.5;
        
        // 设置相机位置
        this.camera.position.set(
            center.x + distance * 0.6,
            center.y + distance * 0.8,
            center.z + distance * 0.6
        );
        
        // 相机朝向中心点
        this.camera.lookAt(center.x, center.y, center.z);
        
        // 更新控制器目标到中心点
        this.controls.target.copy(center);
        this.controls.update();
        
        // 调整网格和坐标轴大小
        if (this.gridHelper) {
            this.scene.remove(this.gridHelper);
            this.gridHelper = new THREE.GridHelper(maxDim * 2, 50, 0xc7c7cc, 0xd1d1d6);
            this.gridHelper.visible = this.settings.showGrid;
            this.scene.add(this.gridHelper);
        }
        
        if (this.axesHelper) {
            this.scene.remove(this.axesHelper);
            this.axesHelper = new THREE.AxesHelper(maxDim * 0.3);
            this.axesHelper.visible = this.settings.showAxes;
            this.scene.add(this.axesHelper);
        }
    }
    
    dispose() {
        // 清理资源
        this.clearRoads();
        
        if (this.renderer) {
            this.renderer.dispose();
        }
        
        if (this.controls) {
            this.controls.dispose();
        }
    }
}

// 导出类
export { Web3DViewer };
window.Web3DViewer = Web3DViewer;