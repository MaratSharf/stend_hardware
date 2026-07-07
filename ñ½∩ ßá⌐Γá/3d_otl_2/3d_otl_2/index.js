/*
 * ========================================
 * ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И КОНФИГУРАЦИЯ
 * ========================================
 */

// Основные объекты Three.js
let scene, camera, renderer, controls;
let pcScreen; // Экран промышленного ПК

// Массивы для хранения элементов сцены
let conveyorRollers = []; // Ролики конвейера
let castingBlocks = []; // Блоки цилиндров
let industrialCameras = []; // Промышленные камеры
let strobeLights = []; // Стробоскопические лампы
let triggerLaserBeam; // Луч лазерного датчика
let cameraFlashes = []; // Массив для вспышек камер
let sideFlashes = []; // Массив для боковых вспышек
let greenSideFlashes = []; // Массив для зеленых боковых вспышек

// Переменные состояния системы
let conveyorIsRunning = true; // Состояние работы конвейера
let conveyorWasRunningBeforeScan = false; // Отслеживает, работал ли конвейер перед сканированием
let isStrobeActive = false; // Состояние стробоскопа
let processedPartCount = 0; // Количество обработанных деталей
let lastProcessedPartTimestamp = 0; // Время последней обработанной детали
const dailyProductionPlan = 100; // План производства на день

// Конфигурация конвейера
const CONVEYOR_SPEED = 0.02; // Скорость движения конвейера
const CASTING_SPAWN_INTERVAL = 200; // Интервал появления новых отливок (в мс)
let animationFrameCount = 0; // Счетчик кадров анимации
let counterCanvas, counterContext, counterTexture;
/*
 * ========================================
 * ФУНКЦИИ ОБНОВЛЕНИЯ ИНТЕРФЕЙСА
 * ========================================
 */

/**
 * Обновляет отображение количества обработанных деталей
 * Обновляет как 2D панель, так и 3D экран
 */
function updatePartCountDisplay() {
    // Update 2D panel
    document.getElementById('part-counter').textContent = `Деталей: ${processedPartCount}`;

    const deviation = processedPartCount - dailyProductionPlan;
    const deviationEl = document.getElementById('production-deviation');

    document.getElementById('production-actual').textContent = processedPartCount;
    deviationEl.textContent = deviation;

    if (deviation < 0) {
        deviationEl.style.color = '#ff6666'; // Red for negative
    } else {
        deviationEl.style.color = '#66ff66'; // Green for positive or zero
    }

    // Update 3D screen
    if (counterContext) {
        // Clear canvas
        if (deviation < 0) {
            counterContext.fillStyle = '#550000';
        } else {
            counterContext.fillStyle = '#005500';
        }
        counterContext.fillRect(0, 0, counterCanvas.width, counterCanvas.height);

        // Draw title
        counterContext.fillStyle = '#ffffff';
        counterContext.font = 'bold 32px Segoe UI';
        counterContext.textAlign = 'center';
        counterContext.fillText('Андон-экран', counterCanvas.width / 2, 40);

        // Draw plan
        counterContext.fillStyle = '#aaaaaa';
        counterContext.font = '24px Segoe UI';
        counterContext.textAlign = 'left';
        counterContext.fillText('План:', 30, 100);

        counterContext.fillStyle = 'white';
        counterContext.font = 'bold 24px Segoe UI';
        counterContext.textAlign = 'right';
        counterContext.fillText(dailyProductionPlan, counterCanvas.width - 30, 100);

        // Draw actual
        counterContext.fillStyle = '#aaaaaa';
        counterContext.font = '24px Segoe UI';
        counterContext.textAlign = 'left';
        counterContext.fillText('Факт:', 30, 150);

        counterContext.fillStyle = '#00ff88';
        counterContext.font = 'bold 36px Segoe UI';
        counterContext.textAlign = 'right';
        counterContext.fillText(processedPartCount, counterCanvas.width - 30, 155);

        // Draw deviation
        counterContext.fillStyle = '#aaaaaa';
        counterContext.font = '24px Segoe UI';
        counterContext.textAlign = 'left';
        counterContext.fillText('Отклонение:', 30, 200);

        counterContext.fillStyle = deviation < 0 ? '#ff6666' : '#66ff66';
        counterContext.font = 'bold 36px Segoe UI';
        counterContext.textAlign = 'right';
        counterContext.fillText(deviation, counterCanvas.width - 30, 205);

        counterTexture.needsUpdate = true;
    }
}

/*
 * ========================================
 * ИНИЦИАЛИЗАЦИЯ СЦЕНЫ
 * ========================================
 */

/**
 * Создает 3D экран для отображения статистики производства
 */
function createCounterScreen() {
    counterCanvas = document.getElementById('counter-canvas');
    counterContext = counterCanvas.getContext('2d');
    counterTexture = new THREE.CanvasTexture(counterCanvas);

    const screenMat = new THREE.MeshBasicMaterial({ map: counterTexture });
    const frameMat = new THREE.MeshBasicMaterial({ color: 0x000000 });

    const materials = [
        frameMat, // right
        frameMat, // left
        frameMat, // top
        frameMat, // bottom
        screenMat, // front
        screenMat  // back
    ];

    const screenGeom = new THREE.BoxGeometry(2, 1, 0.1);
    counterScreen = new THREE.Mesh(screenGeom, materials);

    // Position it above the PC
    counterScreen.position.set(5, 3.5, 4);
    scene.add(counterScreen);
}

/**
 * Инициализирует основные компоненты Three.js и создает сцену
 */
function init() {
    // Настройка сцены
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xc0c0c0); // Lighter background
    scene.fog = new THREE.Fog(0xc0c0c0, 30, 80);  // Lighter fog, matching background

    // Камера
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(15, 12, 15);

    // Рендерер
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.getElementById('canvas-container').appendChild(renderer.domElement);

    // Управление камерой
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 2, 0);

    // Освещение
    setupLighting();

    // Создание элементов сцены
    createFloor();
    createConveyor();
     createPortalFrame();
    createCameras();
    createLights();
    createSideFlashes();
    createGreenSideFlashes();
    createTriggerSensor();
    createIndustrialPC();
    createCabling();
    createCastings();

    // // Добавляем ArrowHelper для отображения осей X, Y, Z
    // const origin = new THREE.Vector3(0, 1.5, 0);
    // const length = 1;

    // // X-axis (Red)
    // const xAxisDir = new THREE.Vector3(1, 0, 0);
    // const xAxisArrow = new THREE.ArrowHelper(xAxisDir, origin, length, 0xff0000);
    // scene.add(xAxisArrow);

    // // Y-axis (Green)
    // const yAxisDir = new THREE.Vector3(0, 1, 0);
    // const yAxisArrow = new THREE.ArrowHelper(yAxisDir, origin, length, 0x00ff00);
    // scene.add(yAxisArrow);

    // // Z-axis (Blue)
    // const zAxisDir = new THREE.Vector3(0, 0, 1);
    // const zAxisArrow = new THREE.ArrowHelper(zAxisDir, origin, length, 0x0000ff);
    // scene.add(zAxisArrow);

    createCounterScreen();

    // Обработка изменения размера окна
    window.addEventListener('resize', onWindowResize);

    // Начальное обновление отображения счетчика
    updatePartCountDisplay();
}

/*
 * ========================================
 * СОЗДАНИЕ ЭЛЕМЕНТОВ СЦЕНЫ
 * ========================================
 */

/**
 * Настраивает освещение сцены
 * Создает основное освещение, дополнительные источники света вдоль конвейера и один общий светильник для зоны проверки
 */
function setupLighting() {
    // Основное освещение - равномерный свет, охватывающий всю сцену
    const ambient = new THREE.AmbientLight(0xffffff, 0.5); // Brighter uniform light
    scene.add(ambient);

    // Добавление дополнительных точечных источников света вдоль конвейера
    // Эти источники обеспечивают общее освещение линии перемещения деталей
    const conveyorLightCount = 5;
    const conveyorLightColor = 0xffffff;
    const conveyorLightIntensity = 0.7; // Ярче свет для линии конвейера
    const conveyorLightDistance = 10;

    for (let i = 0; i < conveyorLightCount; i++) {
        // Распределяем источники света равномерно вдоль оси X (-8 до 8)
        const xPos = -8 + (16 / (conveyorLightCount - 1)) * i; // Распределение от -8 до 8
        const pointLight = new THREE.PointLight(conveyorLightColor, conveyorLightIntensity, conveyorLightDistance);
        pointLight.position.set(xPos, 3, 0); // Позиция над конвейером
        scene.add(pointLight);
    }

    // Добавляем один общий светильник, который освещает всю зону проверки
    const inspectionAreaLight = new THREE.SpotLight(0xffffff, 1.2, 20, Math.PI / 3);
    inspectionAreaLight.position.set(0, 6, 0); // Позиция над областью проверки
    inspectionAreaLight.target.position.set(0, 0, 0); // Направляем свет в центр сцены
    inspectionAreaLight.castShadow = true;

    // Настройки качества теней
    inspectionAreaLight.shadow.mapSize.width = 2048;
    inspectionAreaLight.shadow.mapSize.height = 2048;
    inspectionAreaLight.shadow.camera.near = 0.5;
    inspectionAreaLight.shadow.camera.far = 25;
    inspectionAreaLight.shadow.bias = -0.001; // Уменьшаем артефакты теней

    scene.add(inspectionAreaLight);
}

/**
 * Создает пол с сеткой
 */
function createFloor() {
    // Основной пол
    const floorGeom = new THREE.PlaneGeometry(50, 50);
    const floorMat = new THREE.MeshStandardMaterial({
        color: 0x888899,
        roughness: 0.8,
        metalness: 0.2
    });
    const floor = new THREE.Mesh(floorGeom, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    // Линии сетки
    const gridHelper = new THREE.GridHelper(50, 50, 0x666688, 0x555577);
    gridHelper.position.y = 0.01;
    scene.add(gridHelper);
}

/**
 * Создает конвейерную ленту
 */
function createConveyor() {
    const conveyorLength = 20;
    const conveyorWidth = 2;
    const rollerRadius = 0.1;
    const rollerSpacing = 0.4;

    // Боковые рельсы
    const railGeom = new THREE.BoxGeometry(conveyorLength, 0.5, 0.15);
    const railMat = new THREE.MeshStandardMaterial({
        color: 0xffff00,
        metalness: 0.8,
        roughness: 0.3
    });

    const leftRail = new THREE.Mesh(railGeom, railMat);
    leftRail.position.set(0, 1, conveyorWidth/2 + 0.075);
    leftRail.castShadow = true;
    scene.add(leftRail);

    const rightRail = new THREE.Mesh(railGeom, railMat);
    rightRail.position.set(0, 1, -conveyorWidth/2 - 0.075);
    rightRail.castShadow = true;
    scene.add(rightRail);

    // Ролики
    const rollerGeom = new THREE.CylinderGeometry(rollerRadius, rollerRadius, conveyorWidth, 16);
    const rollerMat = new THREE.MeshStandardMaterial({
        color: 0x888899,
        metalness: 0.9,
        roughness: 0.2
    });

    for (let x = -conveyorLength/2 + rollerSpacing; x < conveyorLength/2; x += rollerSpacing) {
        const roller = new THREE.Mesh(rollerGeom, rollerMat);
        roller.rotation.x = Math.PI / 2;
        roller.position.set(x, 1, 0);
        roller.castShadow = true;
        conveyorRollers.push(roller);
        scene.add(roller);
    }

    // Опорные ножки
    const legGeom = new THREE.BoxGeometry(0.1, 1, 0.1);
    const legMat = new THREE.MeshStandardMaterial({ color: 0x444455, metalness: 0.7 });

    for (let x = -conveyorLength/2 + 1; x <= conveyorLength/2 - 1; x += 3) {
        for (let z of [conveyorWidth/2 + 0.2, -conveyorWidth/2 - 0.2]) {
            const leg = new THREE.Mesh(legGeom, legMat);
            leg.position.set(x, 0.5, z);
            leg.castShadow = true;
            scene.add(leg);
        }
    }
}

/**
 * Создает раму портала для установки камер
 */
function createPortalFrame() {
    const frameMat = new THREE.MeshStandardMaterial({
        color: 0xccccdd,
        metalness: 0.9,
        roughness: 0.2
    });

    // Вертикальные стойки
    const postGeom = new THREE.BoxGeometry(0.15, 4, 0.15);
    const postPositions = [
        [-1.5, 2, 2], [-1.5, 2, -2],
        [1.5, 2, 2], [1.5, 2, -2]
    ];

    postPositions.forEach(pos => {
        const post = new THREE.Mesh(postGeom, frameMat);
        post.position.set(...pos);
        post.castShadow = true;
        scene.add(post);
    });

    // Горизонтальные балки
    const beamGeom1 = new THREE.BoxGeometry(3.3, 0.15, 0.15);
    const beam1 = new THREE.Mesh(beamGeom1, frameMat);
    beam1.position.set(0, 4, 2);
    scene.add(beam1);

    const beam2 = new THREE.Mesh(beamGeom1, frameMat);
    beam2.position.set(0, 4, -2);
    scene.add(beam2);

    // Поперечная балка
    const beamGeom2 = new THREE.BoxGeometry(0.15, 0.15, 4.3);
    const beam3 = new THREE.Mesh(beamGeom2, frameMat);
    beam3.position.set(-1.5, 4, 0);
    scene.add(beam3);

    const beam4 = new THREE.Mesh(beamGeom2, frameMat);
    beam4.position.set(1.5, 4, 0);
    scene.add(beam4);

    // Верхняя плита
    const topPlateGeom = new THREE.BoxGeometry(3.3, 0.1, 4.3);
    const topPlate = new THREE.Mesh(topPlateGeom, frameMat);
    topPlate.position.set(0, 4.15, 0);
    scene.add(topPlate);
}

/**
 * Создает промышленные камеры
 */
function createCameras() {
    const cameraPositions = [
        { pos: [-0.9, 1.7, 1.5], rot: [0, -Math.PI / 4, 0] },  // Подняли камеру на 0.5
        { pos: [0.9, 1.7, 1.5], rot: [0, Math.PI / 4, 0] },   // Подняли камеру на 0.5
        { pos: [-0.9, 1.7, -1.5], rot: [0, -65, 0] },         // Подняли камеру на 0.5
        { pos: [0.9, 1.7, -1.5], rot: [0, 65, 0] }            // Подняли камеру на 0.5
    ];

    cameraPositions.forEach((config, i) => {
        const cameraGroup = createIndustrialCamera();
        cameraGroup.position.set(...config.pos);
        cameraGroup.rotation.set(...config.rot);
        industrialCameras.push(cameraGroup);
        scene.add(cameraGroup);
    });
}

/**
 * Создает модель одной промышленной камеры
 */
function createIndustrialCamera() {
    const group = new THREE.Group();

    // Корпус камеры
    const bodyGeom = new THREE.BoxGeometry(0.3, 0.25, 0.4);
    const bodyMat = new THREE.MeshStandardMaterial({
         color: 0x220000,
        metalness: 0.8,
        roughness: 0.3
    });
    const body = new THREE.Mesh(bodyGeom, bodyMat);
    body.castShadow = true;
    group.add(body);

    // Объектив
    const lensGeom = new THREE.CylinderGeometry(0.08, 0.1, 0.15, 16);
    const lensMat = new THREE.MeshStandardMaterial({
        color: 0x007bff, // Изменено на синий
        metalness: 0.9,
        roughness: 0.1
    });
    const lens = new THREE.Mesh(lensGeom, lensMat);
    lens.rotation.x = Math.PI / 2;
    lens.position.z = -0.25;
    group.add(lens);

    const glassGeom = new THREE.CircleGeometry(0.06, 16);
    const glassMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        metalness: 0.3,
        roughness: 0.1,
        transparent: true,
        opacity: 0.7
    });
    const glass = new THREE.Mesh(glassGeom, glassMat);
    glass.position.z = -0.3;
    group.add(glass);

    // Кронштейн объектива
    const bracketGeom = new THREE.BoxGeometry(0.15, 0.3, 0.08);
    const bracket = new THREE.Mesh(bracketGeom, bodyMat);
    bracket.position.y = -0.2;
    group.add(bracket);

    // Вспышка камеры (похожа на стробоскоп)
    const cameraFlashGroup = new THREE.Group();
    cameraFlashGroup.name = "cameraFlashGroup";

    const flashLedCount = 16; // Меньше светодиодов чем в основном стробе
    const flashLedRadius = 0.12; // Немного больше чем объектив

    const flashLedGeom = new THREE.SphereGeometry(0.01, 8, 8);
    const flashLedMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: 0xffffff,
        emissiveIntensity: 0
    });

    for (let i = 0; i < flashLedCount; i++) {
        const angle = (i / flashLedCount) * Math.PI * 2;
        const led = new THREE.Mesh(flashLedGeom, flashLedMat);
        led.position.set(
            Math.cos(angle) * flashLedRadius,
            Math.sin(angle) * flashLedRadius,
            -0.2 // Позиция немного перед объективом
        );
        cameraFlashGroup.add(led);
    }

    const flashDiffuserGeom = new THREE.RingGeometry(flashLedRadius - 0.02, flashLedRadius + 0.02, 32);
    const flashDiffuserMat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.2
    });
    const flashDiffuser = new THREE.Mesh(flashDiffuserGeom, flashDiffuserMat);
    flashDiffuser.position.z = -0.16; // Позиция немного перед светодиодами
    cameraFlashGroup.add(flashDiffuser);

    // Точечный источник света для эффекта вспышки
    const cameraFlashPointLight = new THREE.PointLight(0xffffff, 0, 2); // Меньшее расстояние чем основной строб
    cameraFlashPointLight.position.z = -0.2;
    cameraFlashPointLight.name = 'cameraFlashPointLight';
    cameraFlashGroup.add(cameraFlashPointLight);

    group.add(cameraFlashGroup); // Добавляем группу вспышки в группу камеры
    cameraFlashes.push(cameraFlashGroup); // Добавляем в глобальный массив для управления

    // Рычаг крепления к раме
    const armMat = new THREE.MeshStandardMaterial({ color: 0x444455, metalness: 0.7, roughness: 0.4 });
    const armGeom = new THREE.BoxGeometry(0.05, 0.8, 0.05);
    const arm = new THREE.Mesh(armGeom, armMat);
    arm.position.set(0, -0.4, 0); // Позиция рычага под камерой
    group.add(arm);

    // Соединитель рычага с рамой
    const connectorGeom = new THREE.BoxGeometry(0.1, 0.05, 0.1);
    const connector = new THREE.Mesh(connectorGeom, armMat);
    connector.position.set(0, -0.75, 0); // Позиция соединителя внизу рычага
    group.add(connector);

    // Светодиод статуса
    const ledGeom = new THREE.SphereGeometry(0.02, 8, 8);
    const ledMat = new THREE.MeshBasicMaterial({ color: 0x00ff00 });
    const led = new THREE.Mesh(ledGeom, ledMat);
    led.position.set(0.1, 0.1, 0.21);
    group.add(led);

    return group;
}

/**
 * Создает стробоскопические светодиодные лампы
 * (Эта функция теперь пустая, так как стробоскопы были удалены и их функциональность перенесена в вспышки камер)
 */
function createLights() {
    // Функция оставлена пустой, так как стробоскопы были удалены
    // Их функциональность теперь реализована в вспышках камер
}

/**
 * Создает боковые светодиодные вспышки для освещения боковых сторон детали.
 */
function createSideFlashes() {
    // Позиции и повороты для 4 вспышек
    const flashConfigs = [
        // { x: -1.4, z: 1.5, rotX: THREE.MathUtils.degToRad(-10), rotY: THREE.MathUtils.degToRad(-5), rotZ: 0 },  // Сзади-слева
        // { x: 1.4,  z: 1.5, rotX: THREE.MathUtils.degToRad(-10), rotY: THREE.MathUtils.degToRad(5), rotZ: 0 },  // Сзади-справа
        // { x: -1.4, z: -1.5, rotX: THREE.MathUtils.degToRad(-10), rotY: THREE.MathUtils.degToRad(-5), rotZ: 0 }, // Спереди-слева
        // { x: 1.4,  z: -1.5, rotX: THREE.MathUtils.degToRad(-10), rotY: THREE.MathUtils.degToRad(5), rotZ: 0 }  // Спереди-справа
          { x: -1.1, z: 1.0, rotX: 0, rotY: 0, rotZ: 0 },  // Сзади-слева
        { x: 1.1,  z: 1.0, rotX: 0, rotY: 0, rotZ: 0 },  // Сзади-справа
        { x: -1.1, z: -1.0, rotX: 0, rotY: 0, rotZ: 0 }, // Спереди-слева
        { x: 1.1,  z: -1.0, rotX: 0, rotY: 0 , rotZ: 0 }  // Спереди-справа
    ];

    flashConfigs.forEach(config => {
        const flashGroup = new THREE.Group();

        // Корпус вспышки
        const bodyGeom = new THREE.BoxGeometry(0.2, 0.8, 0.15);
        const bodyMat = new THREE.MeshStandardMaterial({
            color: 0x333344,
            metalness: 0.8,
            roughness: 0.3
        });
        const body = new THREE.Mesh(bodyGeom, bodyMat);
        flashGroup.add(body);

        // Светящаяся панель (LED)
        const ledGeom = new THREE.PlaneGeometry(0.15, 0.8);
        const ledMat = new THREE.MeshStandardMaterial({
            color: 0xffffff,
            emissive: 0xffffee,
            emissiveIntensity: 0 // Выключен по умолчанию
        });
        const led = new THREE.Mesh(ledGeom, ledMat);
        // Располагаем светодиод на передней части корпуса
        led.position.z = config.z > 0 ? 0.08 : 0.08; // Adjusted led.position.z
        flashGroup.add(led);

        // Точечный свет для эффекта вспышки
        const spotLight = new THREE.SpotLight(0xffffff, 0, 12, Math.PI / 5, 0.4);
        spotLight.position.copy(led.position); // Свет исходит от светодиода

        flashGroup.add(spotLight);
        // Цель света - центр зоны инспекции
        spotLight.target.position.set(0, 1.6, 0);
        flashGroup.add(spotLight.target);

        // Позиционирование и ориентация всей группы
        flashGroup.position.set(config.x, 1.7, config.z);
        // Направляем вспышку на центр зоны инспекции
        flashGroup.lookAt(0, 1.7, 0);

        // Применяем дополнительный поворот из конфигурации
        flashGroup.rotation.x += config.rotX;
        flashGroup.rotation.y += config.rotY;
        flashGroup.rotation.z += config.rotZ;

        // Добавляем в массив для управления в triggerCapture
        sideFlashes.push({ light: spotLight, led: ledMat });
        scene.add(flashGroup);
    });
}

/**
 * Создает боковые зеленые светодиодные вспышки, параллельные ходу конвейера.
 */
function createGreenSideFlashes() {
    // Позиции для 6 вспышек: 3 стопки по 2 вспышки с каждой стороны
    const flashConfigs = [
        { x: 0, y: 1.9, z: 1.5 }, // Левая сторона, середина
        { x: 0, y: 2.3, z: 1.4 }, // Левая сторона, верхняя
        { x: 0, y: 1.9, z: -1.5 },// Правая сторона, середина
        { x: 0, y: 2.3, z: -1.4 }, // Правая сторона, верхняя
        { x: 0, y: 1.5, z: 1.5 }, // Левая сторона, нижняя (дополнительный)
        { x: 0, y: 1.5, z: -1.5 } // Правая сторона, нижняя (дополнительный)
    ];

    flashConfigs.forEach(config => {
        const flashGroup = new THREE.Group();

        // Корпус вспышки (горизонтально)
        const bodyGeom = new THREE.BoxGeometry(0.8, 0.2, 0.15);
        const bodyMat = new THREE.MeshStandardMaterial({
            color: 0xffa500, // Изменено на оранжевый
            metalness: 0.8,
            roughness: 0.3
        });
        const body = new THREE.Mesh(bodyGeom, bodyMat);
        flashGroup.add(body);

        // Светящаяся панель (LED) (горизонтально)
        const ledGeom = new THREE.PlaneGeometry(0.8, 0.15);
        const ledMat = new THREE.MeshStandardMaterial({
            // color: 0x00ff00,
            // emissive: 0x00ff00,
            color: 0xffffff,
            emissive: 0xffffee,
            emissiveIntensity: 0 // Выключен по умолчанию
        });
        const led = new THREE.Mesh(ledGeom, ledMat);
        // Располагаем светодиод на передней части корпуса
        led.rotation.x = 0;
        led.position.y = 0;
        led.position.z = 0.09; // Перемещаем LED панель на другую сторону, чтобы она была направлена на деталь
         flashGroup.add(led); // Отключено отображение LED панели

        // Точечный свет для эффекта вспышки
        const spotLight = new THREE.SpotLight(0xffffff, 0, 12, Math.PI / 5, 0.4);
        spotLight.position.copy(led.position); // Свет исходит от светодиода

        flashGroup.add(spotLight);
        // Цель света - центр зоны инспекции (на деталь)
        spotLight.target.position.set(0, 1.6, 0);
        flashGroup.add(spotLight.target);

        // Позиционирование и ориентация всей группы
        flashGroup.position.set(config.x, config.y, config.z);
        flashGroup.lookAt(0, 1.6, 0);

        // Добавляем в массив для управления в triggerCapture
        greenSideFlashes.push({ light: spotLight, led: ledMat });
        scene.add(flashGroup);
    });
}

/**
 * Создает оптический датчик триггера
 */
function createTriggerSensor() {
    const group = new THREE.Group();

    // Корпус датчика
    const bodyGeom = new THREE.CylinderGeometry(0.05, 0.05, 0.15, 16);
    const bodyMat = new THREE.MeshStandardMaterial({
        color: 0xdd4400,
        metalness: 0.6
    });
    const body = new THREE.Mesh(bodyGeom, bodyMat);
    body.rotation.x = Math.PI / 2;
    group.add(body);

    // Линза
    const lensGeom = new THREE.SphereGeometry(0.03, 16, 16);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
    const lens = new THREE.Mesh(lensGeom, lensMat);
    lens.position.z = 0.08;
    group.add(lens);

    group.position.set(0.5, 1.5, 1.3);
    scene.add(group);

    // Луч триггера
    const beamGeom = new THREE.CylinderGeometry(0.01, 0.01, 2.6, 8);
    const beamMat = new THREE.MeshBasicMaterial({
        color: 0xff0000,
        transparent: true,
        opacity: 0.5
    });
    triggerLaserBeam = new THREE.Mesh(beamGeom, beamMat);
    triggerLaserBeam.rotation.x = Math.PI / 2;
    triggerLaserBeam.position.set(0.5, 1.5, 0);
    scene.add(triggerLaserBeam);
}

/**
 * Создает промышленный компьютер
 */
function createIndustrialPC() {
    const group = new THREE.Group();

    // Основной шкаф
    const cabinetGeom = new THREE.BoxGeometry(0.8, 1.8, 0.6);
    const cabinetMat = new THREE.MeshStandardMaterial({
        color: 0x666677,
        metalness: 0.8,
        roughness: 0.3
    });
    const cabinet = new THREE.Mesh(cabinetGeom, cabinetMat);
    cabinet.position.y = 0.9;
    cabinet.castShadow = true;
    group.add(cabinet);

    // Дверь
    const doorGeom = new THREE.BoxGeometry(0.7, 1.6, 0.05);
    const doorMat = new THREE.MeshStandardMaterial({
        color: 0x555566,
        metalness: 0.9
    });
    const door = new THREE.Mesh(doorGeom, doorMat);
    door.position.set(0, 0.9, 0.32);
    group.add(door);

    // Вентиляция
    for (let y = 0.4; y < 1.5; y += 0.1) {
        const ventGeom = new THREE.BoxGeometry(0.5, 0.02, 0.01);
        const ventMat = new THREE.MeshStandardMaterial({ color: 0x333344 });
        const vent = new THREE.Mesh(ventGeom, ventMat);
        vent.position.set(0, y, 0.35);
        group.add(vent);
    }

    // Светодиоды статуса
    const ledColors = [0x00ff00, 0x00ff00, 0xffaa00, 0x00ff00];
    ledColors.forEach((color, i) => {
        const ledGeom = new THREE.SphereGeometry(0.02, 8, 8);
        const ledMat = new THREE.MeshBasicMaterial({ color });
        const led = new THREE.Mesh(ledGeom, ledMat);
        led.position.set(-0.2 + i * 0.1, 1.6, 0.35);
        group.add(led);
    });

    // Монитор
    const monitorGroup = new THREE.Group();

    // Размеры монитора такие же, как у экрана андона
    const screenGeom = new THREE.BoxGeometry(2, 1, 0.05);
    const screenMat = new THREE.MeshStandardMaterial({ color: 0x111122 });
    const screen = new THREE.Mesh(screenGeom, screenMat);
    monitorGroup.add(screen);

    const displayGeom = new THREE.PlaneGeometry(1.8, 0.8);

    // Создаем канвас для рисования интерфейса
    const interfaceCanvas = document.createElement('canvas');
    interfaceCanvas.width = 512;
    interfaceCanvas.height = 256;
    const interfaceContext = interfaceCanvas.getContext('2d');

    // Белый фон
    interfaceContext.fillStyle = '#ffffff';
    interfaceContext.fillRect(0, 0, interfaceCanvas.width, interfaceCanvas.height);

    // Серый прямоугольник (деталь) в центре
    interfaceContext.fillStyle = '#808080'; // Серый цвет
    const rectWidth = interfaceCanvas.width * 0.6;
    const rectHeight = interfaceCanvas.height * 0.4;
    interfaceContext.fillRect(
        (interfaceCanvas.width - rectWidth) / 2,
        (interfaceCanvas.height - rectHeight) / 2,
        rectWidth,
        rectHeight
    );

    // Добавляем текст "Деталь"
    interfaceContext.fillStyle = '#333333';
    interfaceContext.font = 'bold 36px Arial';
    interfaceContext.textAlign = 'center';
    interfaceContext.textBaseline = 'middle';
    interfaceContext.fillText('Деталь', interfaceCanvas.width / 2, interfaceCanvas.height / 2);

    const interfaceTexture = new THREE.CanvasTexture(interfaceCanvas);
    const displayMat = new THREE.MeshBasicMaterial({ map: interfaceTexture });
    pcScreen = new THREE.Mesh(displayGeom, displayMat);
    pcScreen.position.z = 0.026;
    monitorGroup.add(pcScreen);

    const standGeom = new THREE.BoxGeometry(0.1, 0.3, 0.1);
    const stand = new THREE.Mesh(standGeom, screenMat);
    stand.position.y = -0.45;
    stand.position.z = -0.07;
    monitorGroup.add(stand);

    monitorGroup.position.set(0, 2.4, 0.1);
    monitorGroup.rotation.x = -0.2;
    group.add(monitorGroup);

    group.position.set(5, 0, 4);
    scene.add(group);

    // Сетевой коммутатор
    const switchGeom = new THREE.BoxGeometry(0.4, 0.1, 0.2);
    const switchMat = new THREE.MeshStandardMaterial({ color: 0x222233, metalness: 0.8 });
    const networkSwitch = new THREE.Mesh(switchGeom, switchMat);
    networkSwitch.position.set(5, 1.9, 4.0);
    scene.add(networkSwitch);

    // Светодиоды коммутатора
    for (let i = 0; i < 8; i++) {
        const ledGeom = new THREE.SphereGeometry(0.01, 8, 8);
        const ledMat = new THREE.MeshBasicMaterial({
            color: i < 5 ? 0x00ff00 : 0x333333
        });
        const led = new THREE.Mesh(ledGeom, ledMat);
        led.position.set(4.85 + i * 0.04, 1.9, 3.9);
        scene.add(led);
    }
}


/**
 * Создает кабельную систему (пока пустая функция)
 */
function createCabling() {
    // TODO: Реализовать кабельную систему
}

/**
 * Создает отливки цилиндров
 */
function createCastings() {
    for (let i = 0; i < 3; i++) {
        const casting = createCylinderBlock();
        casting.position.set(-8 + i * 5, 1.6, 0);
        castingBlocks.push(casting);
        scene.add(casting);
    }
}

/**
 * Создает модель одного блока цилиндров
 */
function createCylinderBlock() {
    const group = new THREE.Group();

    const mainMat = new THREE.MeshStandardMaterial({
        color: 0x888899,
        metalness: 0.7,
        roughness: 0.5
    });

    // Основное тело
    const bodyGeom = new THREE.BoxGeometry(1.2, 1.0, 0.8);
    const body = new THREE.Mesh(bodyGeom, mainMat);
    body.castShadow = true;
    group.add(body);

    // Отверстия цилиндров
    for (let i = 0; i < 4; i++) {
        const boreGeom = new THREE.CylinderGeometry(0.12, 0.12, 1.02, 16);
        const boreMat = new THREE.MeshStandardMaterial({
            color: 0x333344,
            metalness: 0.9
        });
        const bore = new THREE.Mesh(boreGeom, boreMat);
        bore.position.set(-0.45 + i * 0.3, 0, 0);
        group.add(bore);
    }

    // Ребра жесткости
    for (let x = -0.5; x <= 0.5; x += 0.25) {
        const ribGeom = new THREE.BoxGeometry(0.05, 1.05, 0.85);
        const rib = new THREE.Mesh(ribGeom, mainMat);
        rib.position.x = x;
        rib.castShadow = true;
        group.add(rib);
    }

    // Боковые фланцы
    const flangeGeom = new THREE.BoxGeometry(1.3, 0.1, 0.1);
    const flange1 = new THREE.Mesh(flangeGeom, mainMat);
    flange1.position.set(0, -0.2, 0.45);
    group.add(flange1);

    const flange2 = new THREE.Mesh(flangeGeom, mainMat);
    flange2.position.set(0, -0.2, -0.45);
    group.add(flange2);

    // Отверстия для болтов
    const boltPositions = [
        [-0.5, 0.45], [-0.25, 0.45], [0.25, 0.45], [0.5, 0.45],
        [-0.5, -0.45], [-0.25, -0.45], [0.25, -0.45], [0.5, -0.45]
    ];

    boltPositions.forEach(([x, z]) => {
        const holeGeom = new THREE.CylinderGeometry(0.03, 0.03, 0.15, 8);
        const holeMat = new THREE.MeshStandardMaterial({ color: 0x222233 });
        const hole = new THREE.Mesh(holeGeom, holeMat);
        hole.position.set(x, -0.2, z);
        group.add(hole);
    });

    // Визуализация случайных дефектов (для демонстрации)
    group.userData.hasDefect = Math.random() > 0.5;
    if (group.userData.hasDefect) {
        const defectGeom = new THREE.SphereGeometry(0.02, 8, 8);
        const defectMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const defect = new THREE.Mesh(defectGeom, defectMat);
        defect.position.set(
            (Math.random() - 0.5) * 0.8,
            0.51,
            (Math.random() - 0.5) * 0.5
        );
        group.add(defect);
    }

    return group;
}

/*
 * ========================================
 * ФУНКЦИИ УПРАВЛЕНИЯ СИСТЕМОЙ
 * ========================================
 */

/**
 * Активирует захват изображения с эффектом вспышки
 */
function triggerCapture(hasDefect) {
    isStrobeActive = true;
    conveyorWasRunningBeforeScan = conveyorIsRunning; // Сохраняем состояние конвейера
    conveyorIsRunning = false; // Останавливаем конвейер

    // Эффект вспышки камер
    cameraFlashes.forEach(flashGroup => {
        flashGroup.children.forEach(child => {
            if (child.material && child.material.emissive !== undefined) {
                child.material.emissiveIntensity = 2;
            }
        });
        const cameraFlashPointLight = flashGroup.getObjectByName('cameraFlashPointLight');
        if (cameraFlashPointLight) cameraFlashPointLight.intensity = 3;
    });

    // Активация боковых вспышек
    sideFlashes.forEach(flash => {
        flash.light.intensity = 2.0;
        flash.led.emissiveIntensity = 2;
    });

    // Активация зеленых боковых вспышек
    greenSideFlashes.forEach(flash => {
        flash.light.intensity = 2.0;
        flash.led.emissiveIntensity = 2;
    });

    // Обновление статуса
    document.getElementById('trigger-status').classList.remove('status-warning');
    document.getElementById('trigger-status').classList.add('status-active');
    document.getElementById('trigger-text').textContent = 'Захват!';

    // Обновление экрана ПК
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 128;
    context.fillStyle = hasDefect ? 'red' : 'green';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.font = 'bold 48px Arial';
    context.fillStyle = 'white';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(hasDefect ? 'ДЕФЕКТ ОБНАРУЖЕН' : 'OK', canvas.width / 2, canvas.height / 2);

    const statusTexture = new THREE.CanvasTexture(canvas);
    const statusMaterial = new THREE.MeshBasicMaterial({ map: statusTexture, transparent: true });
    const statusGeometry = new THREE.PlaneGeometry(1.8, 0.45);
    const statusMesh = new THREE.Mesh(statusGeometry, statusMaterial);
    statusMesh.position.set(5, 2.2, 4.15); // Позиция перед экраном
    scene.add(statusMesh);


    setTimeout(() => {
        isStrobeActive = false;
        scene.remove(statusMesh);

        // Сброс эффекта вспышки камер
        cameraFlashes.forEach(flashGroup => {
            flashGroup.children.forEach(child => {
                if (child.material && child.material.emissive !== undefined) {
                    child.material.emissiveIntensity = 0;
                }
            });
            const cameraFlashPointLight = flashGroup.getObjectByName('cameraFlashPointLight');
            if (cameraFlashPointLight) cameraFlashPointLight.intensity = 0;
        });

        // Деактивация боковых вспышек
        sideFlashes.forEach(flash => {
            flash.light.intensity = 0;
            flash.led.emissiveIntensity = 0;
        });

        // Деактивация зеленых боковых вспышек
        greenSideFlashes.forEach(flash => {
            flash.light.intensity = 0;
            flash.led.emissiveIntensity = 0;
        });

        // Сброс статуса
        document.getElementById('trigger-status').classList.add('status-warning');
        document.getElementById('trigger-status').classList.remove('status-active');
        document.getElementById('trigger-text').textContent = 'Ожидание детали...';

        // Возобновляем работу конвейера, если он работал до сканирования
        if (conveyorWasRunningBeforeScan) {
            conveyorIsRunning = true;
        }

    }, 1000); // Увеличено время для отображения статуса
}

/**
 * Переключает состояние работы конвейера
 */
function toggleConveyor() {
    conveyorIsRunning = !conveyorIsRunning;
}

/**
 * Сбрасывает положение камеры к начальному
 */
function resetCamera() {
    camera.position.set(15, 12, 15);
    controls.target.set(0, 2, 0);
    controls.update();
}

/**
 * Сбрасывает счетчик деталей
 */
function resetPartCounter() {
    processedPartCount = 0;
    updatePartCountDisplay();
}

/**
 * Обрабатывает изменение размера окна
 */
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

/*
 * ========================================
 * АНИМАЦИОННЫЙ ЦИКЛ
 * ========================================
 */

/**
 * Основной анимационный цикл
 */
function animate() {
    requestAnimationFrame(animate);
    animationFrameCount++;

    if (conveyorIsRunning) {
        // Вращение роликов
        conveyorRollers.forEach(roller => {
            roller.rotation.y += 0.05;
        });

        // Движение отливок
        castingBlocks.forEach((casting, i) => {
            casting.position.x += CONVEYOR_SPEED;

            // Проверка зоны триггера
            if (casting.position.x > -0.2 && casting.position.x < 0.2) {
                if (!casting.triggered) {
                    casting.triggered = true;
                    triggerCapture(casting.userData.hasDefect);
                }
            }

            // Сброс позиции отливки и подсчет деталей
            if (casting.position.x > 10) {
                // Защита от многократного подсчета одной и той же детали
                if (Date.now() - lastProcessedPartTimestamp > 100) {
                    processedPartCount++;
                    updatePartCountDisplay();
                    lastProcessedPartTimestamp = Date.now();
                }
                casting.position.x = -10;
                casting.triggered = false;
            }
        });
    }

    // Пульсация луча триггера
    if (triggerLaserBeam) {
        triggerLaserBeam.material.opacity = 0.3 + Math.sin(animationFrameCount * 0.1) * 0.2;
    }

    controls.update();
    renderer.render(scene, camera);

    // Обновление меток каждые несколько кадров
    if (animationFrameCount % 5 === 0) {
        // updateLabels(); // Вызов обновления меток (функция закомментирована)
    }
}
// Инициализация и запуск анимации
init();
animate();