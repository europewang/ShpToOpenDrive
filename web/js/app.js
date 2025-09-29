/**
 * 主应用程序类
 * 处理用户界面交互和API调用
 */
import { Web3DViewer } from './web3d-viewer.js';

class App {
    constructor() {
        this.viewer = null;
        this.currentFile = null;
        
        // 多文件管理数据结构
        this.loadedFiles = new Map(); // 文件ID -> 文件信息映射
        this.fileModels = new Map();  // 文件ID -> 3D模型对象映射
        this.selectedFileId = null;   // 当前选中的文件ID
        this.fileIdCounter = 0;       // 文件ID计数器
        
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
        
        // 更新状态
        this.updateStatus('就绪');
        
        console.log('应用程序初始化完成');
    }
    
    bindEvents() {
        // 清屏按钮
        document.getElementById('loadSampleBtn').addEventListener('click', () => {
            this.clearAllFiles();
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
        
        // 导出OBJ按钮
        document.getElementById('exportObjBtn').addEventListener('click', () => {
            this.showExportModal('obj');
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
        
        // 自定义CRS选择已移除
        
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
    

    
    /**
     * 处理文件选择事件
     * 支持SHP、XODR、OBJ等多种文件格式的自动识别和处理
     * @param {Event} event - 文件选择事件
     */
    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        if (!files || files.length === 0) return;
        
        // 按文件类型分组
        const fileGroups = {
            shp: [],
            xodr: [],
            obj: []
        };
        
        files.forEach(file => {
            const ext = file.name.toLowerCase().split('.').pop();
            if (ext === 'shp' || ext === 'shx' || ext === 'dbf' || ext === 'prj') {
                fileGroups.shp.push(file);
            } else if (ext === 'xodr') {
                fileGroups.xodr.push(file);
            } else if (ext === 'obj') {
                fileGroups.obj.push(file);
            }
        });
        
        // 检查是否有有效文件
        const hasValidFiles = fileGroups.shp.length > 0 || fileGroups.xodr.length > 0 || fileGroups.obj.length > 0;
        if (!hasValidFiles) {
            this.showError('请选择SHP文件(.shp)、OpenDrive文件(.xodr)或OBJ文件(.obj)');
            return;
        }
        
        // 处理每种类型的文件
        if (fileGroups.obj.length > 0) {
            fileGroups.obj.forEach(file => {
                this.loadObjFile(file);
            });
        }
        
        if (fileGroups.xodr.length > 0) {
            fileGroups.xodr.forEach(file => {
                this.convertAndLoadXodrAsObj(file);
            });
        }
        
        if (fileGroups.shp.length > 0) {
            // 对于SHP文件，提供转换选项
            this.showShpConversionOptions(fileGroups.shp);
        }
    }
    
    /**
     * 上传文件到服务器
     * 支持SHP和XODR文件格式的上传和处理
     * @param {Array} files - 要上传的文件数组
     * @param {string} fileType - 文件类型（'shp' 或 'xodr'）
     */
    async uploadFiles(files, fileType = 'shp') {
        if (fileType === 'xodr') {
            this.showLoading(true, '上传XODR文件', '正在解析OpenDRIVE格式...');
        } else {
            this.showLoading(true);
        }
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
                    this.showLoading(true, '转换3D模型', '正在生成道路网格...');
                    this.updateStatus('XODR文件上传成功，正在转换为3D模型...');
                    await this.convertAndLoadXodrAsObj(files[0]);
                } else {
                    // SHP文件显示为线条
                    // 加载到3D查看器（不清空现有模型）
                    const shpModelData = this.viewer.loadGeoJSON(data.data);
                    
                    // 获取坐标偏移量
                    this.fetchCoordinateOffset();
                    
                    // 自动调整视角到可视范围
                    setTimeout(() => {
                        this.viewer.fitCameraToRoads();
                    }, 100);
                    
                    // 添加到文件列表
                    const fileId = this.addFileToList(files[0], fileType, {
                        type: 'SHP线条',
                        filename: data.filename
                    }, shpModelData);
                    
                    // 选中新加载的文件
                    this.selectFile(fileId);
                    
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
    
    showShpConversionOptions(files) {
        // 创建模态对话框
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            max-width: 400px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        `;
        
        modalContent.innerHTML = `
            <h3 style="margin-bottom: 20px; color: #333;">选择转换方式</h3>
            <p style="margin-bottom: 30px; color: #666;">您上传了SHP文件，请选择转换方式：</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button id="convertToXodrBtn" class="btn btn-primary">转换为XODR</button>
                <button id="convertToObjBtn" class="btn btn-success">直接转换为OBJ</button>
            </div>
            <button id="cancelBtn" class="btn btn-secondary" style="margin-top: 15px;">取消</button>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // 绑定事件
        document.getElementById('convertToXodrBtn').onclick = () => {
            document.body.removeChild(modal);
            const organizedFiles = this.organizeShapefileSet(files);
            this.uploadFiles(organizedFiles, 'shp');
        };
        
        document.getElementById('convertToObjBtn').onclick = () => {
            document.body.removeChild(modal);
            this.convertShpToObj(files);
        };
        
        document.getElementById('cancelBtn').onclick = () => {
            document.body.removeChild(modal);
        };
        
        // 点击背景关闭
        modal.onclick = (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        };
    }
    
    /**
     * 将SHP文件直接转换为OBJ格式
     * 跳过XODR中间步骤，直接生成3D模型
     * @param {Array} files - SHP文件数组
     */
    async convertShpToObj(files) {
        try {
            this.showLoading(true);
            this.updateStatus('正在转换SHP文件为OBJ格式...');
            
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });
            
            const response = await fetch('/api/convert_shp_to_obj', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                // 获取转换后的OBJ文件
                const blob = await response.blob();
                const shpFile = files.find(f => f.name.endsWith('.shp'));
                const objFileName = shpFile ? shpFile.name.replace('.shp', '.obj') : 'converted.obj';
                const objFile = new File([blob], objFileName, {
                    type: 'application/octet-stream'
                });
                
                // 使用loadObjFile方法加载，保持多文件管理功能
                await this.loadObjFile(objFile);
                
                // 更新当前选中文件的类型信息
                if (this.selectedFileId && this.loadedFiles.has(this.selectedFileId)) {
                    const fileInfo = this.loadedFiles.get(this.selectedFileId);
                    fileInfo.type = 'OBJ (从SHP转换)';
                    this.updateFileInfo(fileInfo.modelData, fileInfo.name, fileInfo.type);
                }
                
                this.updateStatus('SHP文件已成功转换为OBJ格式并加载到3D查看器');
            } else {
                const errorData = await response.json();
                this.showError(`转换失败: ${errorData.error || '未知错误'}`);
            }
        } catch (error) {
            console.error('转换SHP到OBJ失败:', error);
            this.showError('转换SHP到OBJ失败，请检查文件格式');
        } finally {
            this.showLoading(false);
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
            this.showLoading(true, '转换3D模型', '正在处理OpenDRIVE数据...');
            
            const formData = new FormData();
            formData.append('file', xodrFile);
            
            const response = await fetch('/api/convert_xodr_to_obj', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                this.showLoading(true, '加载3D模型', '正在渲染道路场景...');
                
                // 获取转换后的OBJ文件
                const blob = await response.blob();
                const objFileName = xodrFile.name.replace('.xodr', '.obj');
                const objFile = new File([blob], objFileName, {
                    type: 'application/octet-stream'
                });
                
                // 使用loadObjFile方法加载OBJ文件，保持多文件管理
                const fileId = await this.loadObjFile(objFile, {
                    type: 'OBJ (从XODR转换)',
                    originalFile: xodrFile.name
                });
                
                // 选中新加载的文件
                this.selectFile(fileId);
                
                this.updateStatus(`XODR文件已成功转换为3D模型并显示`);
                
                // 延迟隐藏加载动画，让用户看到完成状态
                setTimeout(() => {
                    this.showLoading(false);
                }, 500);
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || '转换失败');
            }
            
        } catch (error) {
            console.error('转换并加载XODR失败:', error);
            this.showLoading(false);
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
    
    async loadObjFile(file) {
        this.showLoading(true, '加载OBJ文件', '正在解析3D模型...');
        this.updateStatus('加载OBJ文件中...');
        
        try {
            // 使用3D查看器加载OBJ文件，传入进度回调
            const modelData = await this.viewer.loadOBJ(file, (title, text) => {
                this.showLoading(true, title, text);
            });
            
            // 将OBJ文件内容发送到后端保存
            try {
                const formData = new FormData();
                formData.append('obj_file', file);
                formData.append('filename', file.name);
                
                const response = await fetch('/api/save_obj_data', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    console.warn('保存OBJ数据到后端失败:', response.statusText);
                }
            } catch (saveError) {
                console.warn('保存OBJ数据时出错:', saveError);
            }
            
            // 添加到文件列表，包含模型数据
            const fileId = this.addFileToList(file, 'obj', {
                type: 'OBJ',
                filename: file.name,
                size: file.size
            }, modelData);
            
            // 选中新加载的文件
            this.selectFile(fileId);
            
            this.currentFile = file.name;
            this.currentFileType = 'obj'; // 设置当前文件类型为obj
            this.updateStatus(`成功加载OBJ文件: ${file.name}`);
            
            // 延迟隐藏加载动画，让用户看到完成状态
            setTimeout(() => {
                this.showLoading(false);
            }, 500);
            
        } catch (error) {
            console.error('加载OBJ文件失败:', error);
            this.showLoading(false);
            this.showError('加载OBJ文件失败: ' + error.message);
            this.updateStatus('加载失败');
        } finally {
            // 清空文件输入
            document.getElementById('fileInput').value = '';
        }
    }
    
    async loadShpFile(filePath) {
        this.showLoading(true);
        this.updateStatus('加载SHP文件中...');
        
        try {
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
                const shpModelData = this.viewer.loadGeoJSON(data.data);
                
                // 自动调整视角到可视范围
                setTimeout(() => {
                    this.viewer.fitCameraToRoads();
                }, 100); // 稍微延迟确保渲染完成
                
                // 创建虚拟文件对象用于文件列表
                const virtualFile = {
                    name: filePath.split(/[\/\\]/).pop(),
                    size: 0 // SHP文件大小未知
                };
                
                // 添加到文件列表
                const fileId = this.addFileToList(virtualFile, 'shp', {
                    type: 'SHP线条',
                    filename: filePath
                }, shpModelData);
                
                // 选中新加载的文件
                this.selectFile(fileId);
                
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
    
    updateFileInfo(data, filePath, fileType = 'shp') {
        const fileInfo = document.getElementById('fileInfo');
        const fileName = filePath ? filePath.split(/[/]/).pop() : '未知文件';
        
        // 根据文件类型处理不同的数据格式
        let metadata = {};
        let fileTypeDisplay = 'Shapefile';
        
        if (fileType === 'xodr') {
            fileTypeDisplay = 'OpenDrive';
            metadata = data && data.metadata ? data.metadata : {};
        } else if (fileType === 'obj') {
            fileTypeDisplay = 'OBJ模型';
            // 对于OBJ文件，从modelData中提取信息
            if (data && typeof data === 'object') {
                metadata = {
                    feature_count: data.meshCount || 0,
                    vertex_count: data.vertexCount || 0
                };
            }
        } else {
            // SHP文件
            metadata = data && data.metadata ? data.metadata : {};
        }
        
        if (fileType === 'obj') {
            fileInfo.innerHTML = `
                <p><strong>文件名:</strong> ${fileName}</p>
                <p><strong>文件类型:</strong> ${fileTypeDisplay}</p>
                <p><strong>网格数量:</strong> ${metadata.feature_count || 0}</p>
                <p><strong>顶点数量:</strong> ${metadata.vertex_count || 0}</p>
            `;
        } else {
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
    }
    
    showLoading(show, title = '加载中...', text = '请稍候') {
        const loading = document.getElementById('loading');
        const loadingTitle = document.getElementById('loadingTitle');
        const loadingText = document.getElementById('loadingText');
        
        if (loading) {
            loading.style.display = show ? 'block' : 'none';
        }
        
        if (loadingTitle) {
            loadingTitle.textContent = title;
        }
        
        if (loadingText) {
            loadingText.textContent = text;
        }
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
        if (!this.currentFile && this.loadedFiles.size === 0) {
            this.showError('请先加载文件');
            return;
        }
        
        // 调试信息：显示当前文件状态
        console.log('导出调试信息:', {
            currentFile: this.currentFile,
            currentFileType: this.currentFileType,
            selectedFileId: this.selectedFileId,
            loadedFilesCount: this.loadedFiles.size,
            exportType: exportType
        });
        
        if (this.selectedFileId && this.loadedFiles.has(this.selectedFileId)) {
            const fileInfo = this.loadedFiles.get(this.selectedFileId);
            console.log('选中文件信息:', fileInfo);
        }
        
        // 设置弹窗标题
        let title;
        if (exportType === 'xodr') {
            title = '导出为OpenDRIVE格式';
        } else if (exportType === 'shp') {
            title = '导出为Shapefile格式';
        } else if (exportType === 'obj') {
            title = '导出为OBJ格式';
        }
        document.getElementById('exportModalTitle').textContent = title;
        
        // 显示/隐藏相应的选项组
        const xodrOptions = document.getElementById('xodrOptions');
        const objOptions = document.getElementById('objOptions');
        
        // 隐藏所有选项组
        xodrOptions.style.display = 'none';
        objOptions.style.display = 'none';
        
        // 显示对应的选项组
        if (exportType === 'xodr') {
            xodrOptions.style.display = 'block';
        } else if (exportType === 'obj') {
            objOptions.style.display = 'block';
        }
        
        // 设置默认文件名
        const fileName = this.currentFile ? this.currentFile.split(/[\/\\]/).pop().replace(/\.[^/.]+$/, '') : 'export';
        let extension;
        if (exportType === 'xodr') {
            extension = '.xodr';
        } else if (exportType === 'shp') {
            extension = '.shp';
        } else if (exportType === 'obj') {
            extension = '.obj';
        }
        document.getElementById('exportFileName').value = fileName + extension;
        
        // 设置默认值
        if (exportType === 'xodr') {
            // 设置OpenDRIVE默认值（基于config/default.json）
            document.getElementById('configSelect').value = 'default';
            document.getElementById('geometryTolerance').value = '1.0';
            document.getElementById('useArcFitting').checked = false;
            document.getElementById('useSmoothCurves').checked = true;
            document.getElementById('preserveDetail').checked = true;
        } else if (exportType === 'obj') {
            // 设置OBJ默认值（基于xodr2obj.py）
            document.getElementById('objResolution').value = '0.2';
            document.getElementById('objEps').value = '0.1';
            document.getElementById('qualityMode').value = 'medium';
            document.getElementById('withLaneHeight').checked = false;
            document.getElementById('withRoadObjects').checked = false;
            document.getElementById('verboseOutput').checked = false;
        }
        
        // 添加质量模式变化监听器
        if (exportType === 'obj') {
            const qualityModeSelect = document.getElementById('qualityMode');
            const resolutionInput = document.getElementById('objResolution');
            const laneHeightCheckbox = document.getElementById('withLaneHeight');
            
            qualityModeSelect.onchange = function() {
                const mode = this.value;
                if (mode === 'high') {
                    resolutionInput.value = '0.1';
                    laneHeightCheckbox.checked = true;
                } else if (mode === 'medium') {
                    resolutionInput.value = '0.2';
                    laneHeightCheckbox.checked = false;
                } else if (mode === 'low') {
                    resolutionInput.value = '0.5';
                    laneHeightCheckbox.checked = false;
                }
            };
        }
        
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
                exportType: this.exportType
            };
            
            // 根据导出类型收集特定选项
            if (this.exportType === 'xodr') {
                // OpenDRIVE导出选项 - 使用config/default.json的配置
                exportData.configFile = document.getElementById('configSelect').value;
                exportData.geometryTolerance = parseFloat(document.getElementById('geometryTolerance').value);
                exportData.useArcFitting = document.getElementById('useArcFitting').checked;
                exportData.useSmoothCurves = document.getElementById('useSmoothCurves').checked;
                exportData.preserveDetail = document.getElementById('preserveDetail').checked;
            } else if (this.exportType === 'shp') {
                // SHP导出选项 - 只需要文件名
                // 不需要额外的选项
            } else if (this.exportType === 'obj') {
                // OBJ导出选项 - 基于xodr2obj.py的配置
                exportData.resolution = parseFloat(document.getElementById('objResolution').value);
                exportData.eps = parseFloat(document.getElementById('objEps').value);
                exportData.qualityMode = document.getElementById('qualityMode').value;
                exportData.withLaneHeight = document.getElementById('withLaneHeight').checked;
                exportData.withRoadObjects = document.getElementById('withRoadObjects').checked;
                exportData.verboseOutput = document.getElementById('verboseOutput').checked;
                
                // 根据质量模式自动调整参数
                if (exportData.qualityMode === 'high') {
                    exportData.resolution = 0.1;
                    exportData.withLaneHeight = true;
                } else if (exportData.qualityMode === 'medium') {
                    exportData.resolution = 0.2;
                    exportData.withLaneHeight = false;
                } else if (exportData.qualityMode === 'low') {
                    exportData.resolution = 0.5;
                    exportData.withLaneHeight = false;
                }
            }
            
            // 验证输入
            if (!exportData.fileName) {
                throw new Error('请输入文件名');
            }
            
            // 发送导出请求
            let endpoint;
            if (this.exportType === 'xodr') {
                endpoint = '/api/export_xodr';
            } else if (this.exportType === 'shp') {
                endpoint = '/api/export_shp';
            } else if (this.exportType === 'obj') {
                // 根据当前文件类型选择对应的转换API
                let supportedType = false;
                
                // 检查当前文件名
                if (this.currentFile) {
                    const fileName = this.currentFile.toLowerCase();
                    if (fileName.includes('.shp') || fileName.endsWith('.shp')) {
                        endpoint = '/api/convert_shp_to_obj';
                        supportedType = true;
                    } else if (fileName.includes('.xodr') || fileName.endsWith('.xodr')) {
                        endpoint = '/api/convert_xodr_to_obj';
                        supportedType = true;
                    }
                }
                
                // 检查当前文件类型属性
                if (!supportedType && this.currentFileType) {
                    if (this.currentFileType === 'shp' || this.currentFileType === 'shapefile') {
                        endpoint = '/api/convert_shp_to_obj';
                        supportedType = true;
                    } else if (this.currentFileType === 'xodr' || this.currentFileType === 'opendrive') {
                        endpoint = '/api/convert_xodr_to_obj';
                        supportedType = true;
                    }
                }
                
                // 检查已加载文件列表
                if (!supportedType && this.selectedFileId && this.loadedFiles.has(this.selectedFileId)) {
                    const fileInfo = this.loadedFiles.get(this.selectedFileId);
                    const fileType = fileInfo.type.toLowerCase();
                    if (fileType === 'shp' || fileType === 'shapefile') {
                        endpoint = '/api/convert_shp_to_obj';
                        supportedType = true;
                    } else if (fileType === 'xodr' || fileType === 'opendrive') {
                        endpoint = '/api/convert_xodr_to_obj';
                        supportedType = true;
                    } else if (fileType === 'obj' || fileType === 'wavefront') {
                        // OBJ文件可以重新导出为OBJ（使用通用OBJ导出接口）
                        endpoint = '/api/convert_obj_to_obj';
                        supportedType = true;
                    }
                }
                
                // 检查当前文件名是否为OBJ文件
                if (!supportedType && this.currentFile) {
                    const fileName = this.currentFile.toLowerCase();
                    if (fileName.includes('.obj') || fileName.endsWith('.obj')) {
                        endpoint = '/api/convert_obj_to_obj';
                        supportedType = true;
                    }
                }
                
                if (!supportedType) {
                    throw new Error('当前文件类型不支持导出为OBJ格式。支持的文件类型：SHP、XODR、OBJ');
                }
            }
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
    
    // 文件列表管理方法
    addFileToList(file, fileType, additionalInfo = {}, modelData = null) {
        const fileId = `file_${++this.fileIdCounter}`;
        const fileInfo = {
            id: fileId,
            name: file.name,
            type: additionalInfo.type || fileType,
            size: file.size,
            loadTime: new Date(),
            ...additionalInfo
        };
        
        this.loadedFiles.set(fileId, fileInfo);
        if (modelData) {
            this.fileModels.set(fileId, modelData);
        }
        
        this.updateFileListUI();
        return fileId;
    }
    
    removeFileFromList(fileId) {
        if (this.loadedFiles.has(fileId)) {
            // 从3D场景中移除模型
            if (this.fileModels.has(fileId)) {
                const modelData = this.fileModels.get(fileId);
                this.viewer.removeModel(modelData);
                this.fileModels.delete(fileId);
            }
            
            // 从文件列表中移除
            this.loadedFiles.delete(fileId);
            
            // 如果删除的是当前选中的文件，清空选择
            if (this.selectedFileId === fileId) {
                this.selectedFileId = null;
                this.clearFileInfo();
            }
            
            this.updateFileListUI();
        }
    }
    
    clearAllFiles() {
        // 直接清除操作，不弹窗确认
        if (this.loadedFiles.size === 0) {
            this.showError('没有需要清除的文件');
            return;
        }
        
        // 从3D场景中移除所有模型
        this.fileModels.forEach((modelData) => {
            this.viewer.removeModel(modelData);
        });
        
        // 清空所有数据
        this.loadedFiles.clear();
        this.fileModels.clear();
        this.selectedFileId = null;
        this.currentFile = null;
        this.currentFileType = null;
        
        // 更新UI
        this.clearFileInfo();
        this.updateFileListUI();
        
        // 重置3D视角
        this.viewer.resetView();
        
        this.updateStatus('已清除所有文件');
    }
    
    selectFile(fileId) {
        if (this.loadedFiles.has(fileId)) {
            this.selectedFileId = fileId;
            const fileInfo = this.loadedFiles.get(fileId);
            this.updateFileInfo(fileInfo.modelData, fileInfo.name, fileInfo.type);
            this.updateFileListUI();
        }
    }
    
    updateFileListUI() {
        const fileListContainer = document.getElementById('fileList');
        
        if (this.loadedFiles.size === 0) {
            fileListContainer.innerHTML = '<div class="no-files">暂无加载的文件</div>';
            return;
        }
        
        let html = '';
        this.loadedFiles.forEach((fileInfo, fileId) => {
            const isSelected = fileId === this.selectedFileId;
            const fileSize = (fileInfo.size / 1024).toFixed(1) + ' KB';
            const loadTime = fileInfo.loadTime.toLocaleTimeString();
            const fileType = fileInfo.type || 'UNKNOWN';
            
            html += `
                <div class="file-item ${isSelected ? 'selected' : ''}" data-file-id="${fileId}">
                    <div class="file-item-info">
                        <div class="file-item-name">${fileInfo.name}</div>
                        <div class="file-item-type">${fileType.toUpperCase()} • ${fileSize} • ${loadTime}</div>
                    </div>
                    <div class="file-item-actions">
                        <button class="btn-delete" onclick="app.removeFileFromList('${fileId}')" title="删除文件">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3,6 5,6 21,6"></polyline>
                                <path d="m19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        });
        
        fileListContainer.innerHTML = html;
        
        // 绑定点击事件
        fileListContainer.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-delete')) {
                    const fileId = item.dataset.fileId;
                    this.selectFile(fileId);
                }
            });
        });
    }
    
    clearFileInfo() {
        const fileInfoContainer = document.getElementById('fileInfo');
        fileInfoContainer.innerHTML = '<p>选择文件查看详情</p>';
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