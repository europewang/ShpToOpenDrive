/**
 * 主应用程序类
 * 处理用户界面交互和API调用
 */
import { Web3DViewer } from './web3d-viewer.js';

class App {
    constructor() {
        this.viewer = null;
        this.currentFile = null;
        this.init();
    }
    
    // 组织Shapefile文件集，自动包含同名的相关文件
    organizeShapefileSet(files) {
        const fileMap = new Map();
        const shapefileExtensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.sbn', '.sbx'];
        
        // 将文件按基础名称分组
        files.forEach(file => {
            const fileName = file.name;
            const lastDotIndex = fileName.lastIndexOf('.');
            if (lastDotIndex === -1) return;
            
            const baseName = fileName.substring(0, lastDotIndex).toLowerCase();
            const extension = fileName.substring(lastDotIndex).toLowerCase();
            
            if (shapefileExtensions.includes(extension)) {
                if (!fileMap.has(baseName)) {
                    fileMap.set(baseName, []);
                }
                fileMap.get(baseName).push(file);
            }
        });
        
        // 找到包含.shp文件的文件组
        let selectedFileSet = [];
        for (const [baseName, fileGroup] of fileMap) {
            const hasShpFile = fileGroup.some(file => 
                file.name.toLowerCase().endsWith('.shp')
            );
            
            if (hasShpFile) {
                selectedFileSet = fileGroup;
                console.log(`自动选择Shapefile文件集: ${baseName}`, fileGroup.map(f => f.name));
                break;
            }
        }
        
        if (selectedFileSet.length === 0) {
             this.showError('未找到有效的Shapefile文件集');
             return [];
         }
         
         // 检查必需的文件
         const hasShp = selectedFileSet.some(f => f.name.toLowerCase().endsWith('.shp'));
         const hasShx = selectedFileSet.some(f => f.name.toLowerCase().endsWith('.shx'));
         const hasDbf = selectedFileSet.some(f => f.name.toLowerCase().endsWith('.dbf'));
         
         // 检查所有必需的文件（根据后端要求）
         if (!hasShp) {
             this.showError('缺少必需的.shp文件');
             return [];
         }
         
         if (!hasShx) {
             this.showError('缺少必需的.shx文件');
             return [];
         }
         
         if (!hasDbf) {
             this.showError('缺少必需的.dbf文件');
             return [];
         }
         
         // 显示文件组织信息
         const baseName = selectedFileSet[0].name.substring(0, selectedFileSet[0].name.lastIndexOf('.'));
         const fileNames = selectedFileSet.map(f => f.name).join(', ');
         this.updateStatus(`已自动组织Shapefile文件集: ${baseName} (${selectedFileSet.length}个文件)`);
         
         return selectedFileSet;
    }
    
    init() {
        // 初始化3D查看器
        this.viewer = new Web3DViewer('viewer');
        
        // 绑定事件
        this.bindEvents();
        
        // 加载示例文件列表
        this.loadSampleFiles();
        
        // 更新状态
        this.updateStatus('就绪');
        
        console.log('应用程序初始化完成');
    }
    
    bindEvents() {
        // 加载示例文件按钮
        document.getElementById('loadSampleBtn').addEventListener('click', () => {
            this.showSampleFilesModal();
        });
        
        // 加载本地文件按钮
        document.getElementById('loadFileBtn').addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
        
        // 文件输入
        document.getElementById('fileInput').addEventListener('change', (e) => {
            this.handleFileSelect(e);
        });
        
        // 重置视角按钮
        document.getElementById('resetViewBtn').addEventListener('click', () => {
            this.viewer.resetView();
        });
        
        // 导出XODR按钮
        document.getElementById('exportXodrBtn').addEventListener('click', () => {
            this.showExportModal('xodr');
        });
        
        // 导出SHP按钮
        document.getElementById('exportShpBtn').addEventListener('click', () => {
            this.showExportModal('shp');
        });
        
        // 显示设置
        document.getElementById('showGrid').addEventListener('change', (e) => {
            this.viewer.setShowGrid(e.target.checked);
        });
        
        document.getElementById('showAxes').addEventListener('change', (e) => {
            this.viewer.setShowAxes(e.target.checked);
        });
        
        document.getElementById('lineWidth').addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            const slider = e.target;
            const percentage = ((value - slider.min) / (slider.max - slider.min)) * 100;
            slider.style.background = `linear-gradient(to right, #8e8e93 0%, #8e8e93 ${percentage}%, #ffffff ${percentage}%, #ffffff 100%)`;
            document.getElementById('lineWidthValue').textContent = value;
            this.viewer.setLineWidth(value);
        });
        
        document.getElementById('lineColor').addEventListener('change', (e) => {
            const color = parseInt(e.target.value.replace('#', '0x'));
            this.viewer.setLineColor(color);
        });
        
        // 模态对话框
        document.querySelector('.close').addEventListener('click', () => {
            this.hideModal();
        });
        
        document.getElementById('modalCancel').addEventListener('click', () => {
            this.hideModal();
        });
        
        // 点击模态背景关闭
        document.getElementById('modal').addEventListener('click', (e) => {
            if (e.target.id === 'modal') {
                this.hideModal();
            }
        });
        
        // 导出弹窗事件
        document.getElementById('exportModalClose').addEventListener('click', () => {
            this.hideExportModal();
        });
        
        document.getElementById('exportCancelBtn').addEventListener('click', () => {
            this.hideExportModal();
        });
        
        document.getElementById('exportConfirmBtn').addEventListener('click', () => {
            this.handleExport();
        });
        
        // 自定义CRS选择
        document.getElementById('exportCRS').addEventListener('change', (e) => {
            const customGroup = document.getElementById('customCRSGroup');
            if (e.target.value === 'custom') {
                customGroup.style.display = 'block';
            } else {
                customGroup.style.display = 'none';
            }
        });
        
        // 点击导出弹窗背景关闭
        document.getElementById('exportModal').addEventListener('click', (e) => {
            if (e.target.id === 'exportModal') {
                this.hideExportModal();
            }
        });
        
        // 初始化滑块背景
        this.initSliderBackground();
    }
    
    initSliderBackground() {
        const slider = document.getElementById('lineWidth');
        if (slider) {
            const value = parseInt(slider.value);
            const percentage = ((value - slider.min) / (slider.max - slider.min)) * 100;
            slider.style.background = `linear-gradient(to right, #8e8e93 0%, #8e8e93 ${percentage}%, #ffffff ${percentage}%, #ffffff 100%)`;
        }
    }
    
    async loadSampleFiles() {
        const container = document.getElementById('sampleFiles');
        if (!container) {
            // 示例文件面板不存在，跳过加载
            return;
        }
        
        try {
            const response = await fetch('/api/get_sample_files');
            const data = await response.json();
            
            if (data.files && data.files.length > 0) {
                container.innerHTML = '';
                data.files.forEach(file => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'sample-file';
                    fileDiv.textContent = file.name;
                    fileDiv.addEventListener('click', () => {
                        this.loadShpFile(file.path);
                    });
                    container.appendChild(fileDiv);
                });
            } else {
                container.innerHTML = '<p>没有找到示例文件</p>';
            }
        } catch (error) {
            console.error('加载示例文件列表失败:', error);
            if (container) {
                container.innerHTML = '<p>加载失败</p>';
            }
        }
    }
    
    showSampleFilesModal() {
        this.showModal('选择示例文件', `
            <div id="modalSampleFiles">
                <p>请选择要加载的示例SHP文件：</p>
                <div id="modalFileList"></div>
            </div>
        `);
        
        // 在模态框中显示文件列表
        this.loadSampleFilesInModal();
    }
    
    async loadSampleFilesInModal() {
        try {
            const response = await fetch('/api/get_sample_files');
            const data = await response.json();
            
            const container = document.getElementById('modalFileList');
            
            if (data.files && data.files.length > 0) {
                container.innerHTML = '';
                data.files.forEach(file => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'sample-file';
                    fileDiv.textContent = file.name;
                    fileDiv.style.margin = '0.5rem 0';
                    fileDiv.addEventListener('click', () => {
                        this.loadShpFile(file.path);
                        this.hideModal();
                    });
                    container.appendChild(fileDiv);
                });
            } else {
                container.innerHTML = '<p>没有找到示例文件</p>';
            }
        } catch (error) {
            console.error('加载示例文件列表失败:', error);
            document.getElementById('modalFileList').innerHTML = '<p>加载失败</p>';
        }
    }
    
    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        if (!files || files.length === 0) return;
        
        // 检查文件类型
        const hasShp = files.some(file => file.name.toLowerCase().endsWith('.shp'));
        const hasXodr = files.some(file => file.name.toLowerCase().endsWith('.xodr'));
        const hasObj = files.some(file => file.name.toLowerCase().endsWith('.obj'));
        
        if (!hasShp && !hasXodr && !hasObj) {
            this.showError('请选择SHP文件(.shp)、OpenDrive文件(.xodr)或OBJ文件(.obj)');
            return;
        }
        
        const fileTypeCount = [hasShp, hasXodr, hasObj].filter(Boolean).length;
        if (fileTypeCount > 1) {
            this.showError('请只选择一种文件类型：SHP文件、OpenDrive文件或OBJ文件');
            return;
        }
        
        // 处理不同类型的文件
        if (hasObj) {
            this.loadObjFile(files[0]);
        } else if (hasShp) {
            // 对于SHP文件，自动组织同名的相关文件
            const organizedFiles = this.organizeShapefileSet(files);
            this.uploadFiles(organizedFiles, 'shp');
        } else {
            this.uploadFiles(files, 'xodr');
        }
    }
    
    async uploadFiles(files, fileType = 'shp') {
        this.showLoading(true);
        this.updateStatus(`上传${fileType.toUpperCase()}文件中...`);
        
        try {
            const formData = new FormData();
            if (fileType === 'xodr') {
                // XODR文件只上传单个文件
                formData.append('file', files[0]);
            } else {
                // SHP文件可能包含多个相关文件
                files.forEach(file => {
                    formData.append('files', file);
                });
            }
            
            const apiEndpoint = fileType === 'xodr' ? '/api/upload_xodr' : '/api/upload_shp';
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentFile = data.filename;
                this.currentFileType = fileType;
                
                if (fileType === 'xodr') {
                    // XODR文件自动转换为OBJ并显示3D模型
                    this.updateStatus('XODR文件上传成功，正在转换为3D模型...');
                    await this.convertAndLoadXodrAsObj(files[0]);
                } else {
                    // SHP文件显示为线条
                    // 清空当前画布
                    this.viewer.clearRoads();
                    
                    // 加载到3D查看器
                    this.viewer.loadGeoJSON(data.data);
                    
                    // 获取坐标偏移量
                    this.fetchCoordinateOffset();
                    
                    // 自动调整视角到可视范围
                    setTimeout(() => {
                        this.viewer.fitCameraToRoads();
                    }, 100);
                    
                    // 更新文件信息
                    this.updateFileInfo(data.data, data.filename, fileType);
                    this.updateStatus(`成功上传并加载: ${data.message}`);
                }
            } else {
                throw new Error(data.error || '上传失败');
            }
        } catch (error) {
            console.error('上传文件失败:', error);
            this.showError('上传失败: ' + error.message);
            this.updateStatus('上传失败');
        } finally {
            this.showLoading(false);
            // 清空文件输入
            document.getElementById('fileInput').value = '';
        }
    }
    
    async fetchCoordinateOffset() {
        try {
            const response = await fetch('/api/get_coordinate_offset');
            const data = await response.json();
            
            if (data.success && data.coordinate_offset) {
                const offset = data.coordinate_offset;
                console.log('获取到坐标偏移量:', offset);
                
                // 设置到3D查看器
                this.viewer.setCoordinateOffset(offset.x, offset.y);
            } else {
                console.warn('无法获取坐标偏移量:', data.error);
            }
        } catch (error) {
            console.error('获取坐标偏移量失败:', error);
        }
    }
    
    showXodrToObjOption() {
        // 检查是否已经有转换按钮
        if (document.getElementById('convertToObjBtn')) {
            return;
        }
        
        // 创建转换按钮
        const convertBtn = document.createElement('button');
        convertBtn.id = 'convertToObjBtn';
        convertBtn.className = 'btn btn-success';
        convertBtn.textContent = '转换为OBJ格式';
        convertBtn.style.marginLeft = '10px';
        convertBtn.onclick = () => this.convertXodrToObj();
        
        // 添加到控制面板
        const controls = document.querySelector('.controls');
        controls.appendChild(convertBtn);
    }
    
    async convertAndLoadXodrAsObj(xodrFile) {
        try {
            // 清空当前画布
            this.viewer.clearRoads();
            
            const formData = new FormData();
            formData.append('file', xodrFile);
            
            const response = await fetch('/api/convert_xodr_to_obj', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // 获取转换后的OBJ文件
                const blob = await response.blob();
                const objFile = new File([blob], this.currentFile.replace('.xodr', '.obj'), {
                    type: 'application/octet-stream'
                });
                
                // 直接加载OBJ文件到3D查看器
                this.viewer.loadOBJ(objFile);
                
                // 更新文件信息
                this.updateFileInfo({
                    type: 'OBJ (从XODR转换)',
                    filename: objFile.name,
                    size: objFile.size
                }, objFile.name, 'obj');
                
                this.updateStatus(`XODR文件已成功转换为3D模型并显示`);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || '转换失败');
            }
            
        } catch (error) {
            console.error('转换并加载XODR失败:', error);
            this.showError('转换失败: ' + error.message);
            this.updateStatus('转换失败');
        }
    }
    
    async convertXodrToObj() {
        if (!this.currentFile || this.currentFileType !== 'xodr') {
            this.showError('请先上传XODR文件');
            return;
        }
        
        this.showLoading(true);
        this.updateStatus('正在转换XODR到OBJ格式...');
        
        try {
            // 重新上传文件进行转换
            const fileInput = document.getElementById('fileInput');
            const files = fileInput.files;
            
            if (!files || files.length === 0) {
                this.showError('无法获取原始XODR文件，请重新上传');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', files[0]);
            
            const response = await fetch('/api/convert_xodr_to_obj', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // 下载转换后的OBJ文件
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = this.currentFile.replace('.xodr', '.obj');
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                this.updateStatus('XODR文件已成功转换为OBJ格式并下载');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || '转换失败');
            }
            
        } catch (error) {
            console.error('转换XODR到OBJ失败:', error);
            this.showError('转换失败: ' + error.message);
            this.updateStatus('转换失败');
        } finally {
            this.showLoading(false);
        }
    }
    
    loadObjFile(file) {
        this.showLoading(true);
        this.updateStatus('加载OBJ文件中...');
        
        try {
            // 使用3D查看器加载OBJ文件
            this.viewer.loadOBJ(file);
            
            this.currentFile = file.name;
            this.updateStatus(`成功加载OBJ文件: ${file.name}`);
            
            // 更新文件信息
            this.updateFileInfo({
                type: 'OBJ',
                filename: file.name,
                size: file.size
            }, file.name, 'obj');
            
        } catch (error) {
            console.error('加载OBJ文件失败:', error);
            this.showError('加载OBJ文件失败: ' + error.message);
            this.updateStatus('加载失败');
        } finally {
            this.showLoading(false);
            // 清空文件输入
            document.getElementById('fileInput').value = '';
        }
    }
    
    async loadShpFile(filePath) {
        this.showLoading(true);
        this.updateStatus('加载SHP文件中...');
        
        try {
            // 清空当前画布
            this.viewer.clearRoads();
            
            const response = await fetch('/api/load_shp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ shp_path: filePath })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 加载到3D查看器
                this.viewer.loadGeoJSON(data.data);
                
                // 自动调整视角到可视范围
                setTimeout(() => {
                    this.viewer.fitCameraToRoads();
                }, 100); // 稍微延迟确保渲染完成
                
                // 更新文件信息
                this.updateFileInfo(data.data, filePath, 'shp');
                
                this.currentFile = filePath;
                this.updateStatus(`成功加载: ${data.message}`);
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载SHP文件失败:', error);
            this.showError('加载失败: ' + error.message);
            this.updateStatus('加载失败');
        } finally {
            this.showLoading(false);
        }
    }
    
    updateFileInfo(geojson, filePath, fileType = 'shp') {
        const fileInfo = document.getElementById('fileInfo');
        const fileName = filePath ? filePath.split(/[\/]/).pop() : '未知文件';
        const metadata = geojson.metadata || {};
        const fileTypeDisplay = fileType === 'xodr' ? 'OpenDrive' : 'Shapefile';
        
        fileInfo.innerHTML = `
            <p><strong>文件名:</strong> ${fileName}</p>
            <p><strong>文件类型:</strong> ${fileTypeDisplay}</p>
            <p><strong>道路数量:</strong> ${metadata.feature_count || 0}</p>
            <p><strong>坐标范围:</strong></p>
            <ul>
                <li>X: ${metadata.bounds && metadata.bounds.min_x !== undefined ? metadata.bounds.min_x.toFixed(2) : 'N/A'} ~ ${metadata.bounds && metadata.bounds.max_x !== undefined ? metadata.bounds.max_x.toFixed(2) : 'N/A'}</li>
                <li>Y: ${metadata.bounds && metadata.bounds.min_y !== undefined ? metadata.bounds.min_y.toFixed(2) : 'N/A'} ~ ${metadata.bounds && metadata.bounds.max_y !== undefined ? metadata.bounds.max_y.toFixed(2) : 'N/A'}</li>
            </ul>
            <p><strong>中心点:</strong> (${metadata.center && metadata.center[0] !== undefined ? metadata.center[0].toFixed(2) : 'N/A'}, ${metadata.center && metadata.center[1] !== undefined ? metadata.center[1].toFixed(2) : 'N/A'})</p>
        `;
    }
    
    showLoading(show) {
        const loading = document.getElementById('loading');
        loading.style.display = show ? 'block' : 'none';
    }
    
    showError(message) {
        const error = document.getElementById('error');
        error.textContent = message;
        error.style.display = 'block';
        setTimeout(() => {
            error.style.display = 'none';
        }, 5000);
    }
    
    showWarning(message) {
        // 使用console.warn显示警告，也可以考虑添加UI警告显示
        console.warn(message);
        // 可以在状态栏显示警告信息
        this.updateStatus(message);
        // 3秒后清除警告状态
        setTimeout(() => {
            this.updateStatus('就绪');
        }, 3000);
    }
    
    updateStatus(message) {
        const status = document.getElementById('status');
        if (status) {
            status.textContent = message;
        }
    }
    
    showModal(title, content) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = content;
        document.getElementById('modal').style.display = 'block';
    }
    
    hideModal() {
        document.getElementById('modal').style.display = 'none';
    }
    
    showExportModal(exportType) {
        if (!this.currentFile) {
            this.showError('请先加载文件');
            return;
        }
        
        // 设置弹窗标题
        const title = exportType === 'xodr' ? '导出为OpenDRIVE格式' : '导出为Shapefile格式';
        document.getElementById('exportModalTitle').textContent = title;
        
        // 显示/隐藏相应的选项组
        const xodrOptions = document.getElementById('xodrOptions');
        const shpOptions = document.getElementById('shpOptions');
        
        if (exportType === 'xodr') {
            xodrOptions.style.display = 'block';
            shpOptions.style.display = 'none';
        } else {
            xodrOptions.style.display = 'none';
            shpOptions.style.display = 'block';
        }
        
        // 设置默认文件名
        const fileName = this.currentFile ? this.currentFile.split(/[\/\\]/).pop().replace(/\.[^/.]+$/, '') : 'export';
        const extension = exportType === 'xodr' ? '.xodr' : '.shp';
        document.getElementById('exportFileName').value = fileName + extension;
        
        // 存储导出类型
        this.exportType = exportType;
        
        // 显示弹窗
        document.getElementById('exportModal').style.display = 'block';
    }
    
    hideExportModal() {
        document.getElementById('exportModal').style.display = 'none';
    }
    
    async handleExport() {
        try {
            this.showLoading(true);
            
            // 收集表单数据
            const exportData = {
                fileName: document.getElementById('exportFileName').value,
                crs: document.getElementById('exportCRS').value,
                customCRS: document.getElementById('customCRS').value,
                exportType: this.exportType
            };
            
            // 根据导出类型收集特定选项
            if (this.exportType === 'xodr') {
                exportData.xodrVersion = document.getElementById('xodrVersion').value;
                exportData.roadWidth = parseFloat(document.getElementById('roadWidth').value);
                exportData.laneCount = parseInt(document.getElementById('laneCount').value);
                exportData.includeElevation = document.getElementById('includeElevation').checked;
            } else {
                exportData.includeAttributes = document.getElementById('includeAttributes').checked;
                exportData.geometryType = document.getElementById('geometryType').value;
            }
            
            // 验证输入
            if (!exportData.fileName) {
                throw new Error('请输入文件名');
            }
            
            if (exportData.crs === 'custom' && !exportData.customCRS) {
                throw new Error('请输入自定义坐标参考系统');
            }
            
            // 发送导出请求
            const endpoint = this.exportType === 'xodr' ? '/api/export_xodr' : '/api/export_shp';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(exportData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '导出失败');
            }
            
            // 处理文件下载
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = exportData.fileName;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.hideExportModal();
            this.updateStatus('导出完成');
            
        } catch (error) {
            console.error('导出失败:', error);
            this.showError('导出失败: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
}

// 应用程序启动
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});

// 错误处理
window.addEventListener('error', (e) => {
    console.error('应用程序错误:', e.error);
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('未处理的Promise拒绝:', e.reason);
});