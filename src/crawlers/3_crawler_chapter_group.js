const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

// ==================================================================
// ⚙️ CẤU HÌNH CHẠY
// ==================================================================
const CONFIG = {
    START_INDEX: 0, 
    COUNT: 22, 
    OUTPUT_FILE: '../../data/icd10_structure.json',
    DELAY_AFTER_CLICK: 2000, 
    DELAY_AFTER_EXPAND: 3000 
};
// ==================================================================

class ICD10StructureCrawler {
  constructor() {
    this.browser = null;
    this.page = null;
    this.data = [];
  }

  async start() {
    console.log('🚀 [STRUCTURE] Khởi động browser...');
    this.browser = await puppeteer.launch({
      headless: false,
      args: ['--start-maximized', '--no-sandbox'],
      defaultViewport: null
    });

    this.page = await this.browser.newPage();
    await this.page.setViewport({ width: 1920, height: 1080 });

    console.log('📡 Đang truy cập trang web...');
    await this.page.goto('https://icd.kcb.vn/icd-10/icd10', {
      waitUntil: 'networkidle2',
      timeout: 60000
    });

    await this.page.waitForSelector('mat-tree[role="tree"]', { timeout: 30000 });
    await this.sleep(3000);
    
    // ============================================
    // 🎯 THÊM: TỰ ĐỘNG BẤM "TẤT CẢ" TRƯỚC KHI CRAWL
    // ============================================
    console.log('🔍 Đang tìm và bấm nút "Tất cả"...');
    await this.clickTatCaButton();
    
    console.log('✅ Trang web đã load xong!\n');
  }

  // ============================================
  // HÀM MỚI: TỰ ĐỘNG BẤM "TẤT CẢ"
  // ============================================
  async clickTatCaButton() {
    try {
      // Cách 1: Tìm dropdown trigger và click
      const dropdownTrigger = await this.page.$('div[role="listbox"], mat-select, .mat-select-trigger');
      if (dropdownTrigger) {
        console.log('   → Tìm thấy dropdown, đang mở...');
        await dropdownTrigger.click();
        await this.sleep(1000);
        
        // Tìm option "Tất cả" trong dropdown
        const tatCaOption = await this.page.evaluateHandle(() => {
          const options = Array.from(document.querySelectorAll('mat-option, .mat-option'));
          return options.find(opt => 
            opt.textContent.trim() === 'Tất cả' || 
            opt.textContent.trim().includes('Tất cả')
          );
        });
        
        const hasOption = await tatCaOption.evaluate(opt => opt !== null && opt !== undefined);
        if (hasOption) {
          console.log('   → Tìm thấy "Tất cả", đang click...');
          await tatCaOption.click();
          await this.sleep(2000);
          console.log('   ✅ Đã chọn "Tất cả"!');
          return true;
        }
      }
      
      // Cách 2: Tìm trực tiếp text "Tất cả" và click
      const clicked = await this.page.evaluate(() => {
        const elements = Array.from(document.querySelectorAll('*'));
        const tatCaEl = elements.find(el => {
          const text = el.textContent.trim();
          return text === 'Tất cả' && el.offsetParent !== null;
        });
        if (tatCaEl) {
          tatCaEl.click();
          return true;
        }
        return false;
      });
      
      if (clicked) {
        await this.sleep(2000);
        console.log('   ✅ Đã click "Tất cả"!');
        return true;
      }
      
      console.log('   ⚠️ Không tìm thấy nút "Tất cả", tiếp tục crawl...');
      return false;
      
    } catch (error) {
      console.log('   ⚠️ Lỗi khi click "Tất cả":', error.message);
      return false;
    }
  }

  sleep(ms) { 
    return new Promise(resolve => setTimeout(resolve, ms)); 
  }

  async clickNodeInTree(nodeId, nodeCode) {
    try {
      const idNoDot = nodeId.replace(/\./g, '');
      const selector = `
          mat-nested-tree-node[id="${nodeId}"] span.cursor-pointer, 
          mat-tree-node[id="${nodeId}"] span.cursor-pointer,
          mat-nested-tree-node[id="${idNoDot}"] span.cursor-pointer, 
          mat-tree-node[id="${idNoDot}"] span.cursor-pointer
      `;
      
      const contentSelector = '.block-chapter, .block-disease, .block-type, .block-section';
      const oldText = await this.page.evaluate((sel) => {
          const el = document.querySelector(sel);
          return el ? el.innerText.trim() : "";
      }, contentSelector);

      await this.page.evaluate((sel) => {
        const span = document.querySelector(sel);
        if (span) {
            span.scrollIntoView({ block: 'center' });
            span.click();
        }
      }, selector);
      
      try { 
        await this.page.waitForNetworkIdle({ idleTime: 500, timeout: 3000 }); 
      } catch(e) {}

      try {
          await this.page.waitForFunction(
              (oldContent, sel) => {
                  const container = document.querySelector(sel);
                  if (!container) return false;
                  const newContent = container.innerText.trim();
                  return newContent.length > 0 && newContent !== oldContent;
              },
              { timeout: 5000 }, oldText, contentSelector
          );
      } catch (e) {}

      return true;
    } catch (error) { 
      return false; 
    }
  }

  async expandNodeInTree(nodeId) {
    try {
      const idNoDot = nodeId.replace(/\./g, '');
      const selector = `
          mat-nested-tree-node[id="${nodeId}"], mat-tree-node[id="${nodeId}"],
          mat-nested-tree-node[id="${idNoDot}"], mat-tree-node[id="${idNoDot}"]
      `;
      
      const isExpanded = await this.page.$eval(selector, el => 
        el.getAttribute('aria-expanded') === 'true'
      ).catch(() => false);

      if (isExpanded) return true;

      const toggleButton = await this.page.evaluateHandle((sel) => {
        const node = document.querySelector(sel);
        if (!node) return null;
        return node.querySelector('button.mattreenodetoggle') || 
               node.querySelector('button[aria-label*="Toggle"]');
      }, selector);

      const toggleExists = await toggleButton.evaluate(btn => btn !== null);
      if (!toggleExists) return false; 

      await toggleButton.click();
      await this.sleep(CONFIG.DELAY_AFTER_EXPAND);
      return true;

    } catch (error) {
      return false;
    }
  }

  async getSmartDescription(code, name) {
    try {
      const selector = '.block-chapter, .block-disease, .block-type, .block-section';
      const hasContent = await this.page.waitForSelector(selector, { timeout: 2000 })
        .catch(() => false);
      if (!hasContent) return "";

      return await this.page.evaluate((targetCode, targetName, sel) => {
        const container = document.querySelector(sel);
        if (!container) return "";

        let fullText = "";
        let skipNextUl = false;
        
        const cleanStr = (str) => str.replace(/\s+/g, ' ').trim().toLowerCase();
        const targetStr = cleanStr(`${targetCode} ${targetName}`); 
        const targetCodeOnly = cleanStr(targetCode);

        const children = Array.from(container.children);

        for (const el of children) {
          let text = el.innerText.trim();
          if (!text) continue;
          
          const lowerText = text.toLowerCase();
          const tagName = el.tagName;
          const cleanText = cleanStr(text);

          if (el.classList.contains('chapter') || 
              el.classList.contains('section') || 
              el.classList.contains('type')) {
              continue;
          }

          if (cleanText === targetStr || 
              cleanText === targetCodeOnly || 
              cleanText === cleanStr(targetName) || 
              cleanText.startsWith(`chương ${targetCodeOnly}`) ||
              cleanText.startsWith(`${targetCodeOnly}:`) ||
              (cleanText.includes(targetStr) && text.length < targetStr.length + 50)
             ) {
            continue;
          }

          if (tagName === 'P' && (
              lowerText.includes('chương này chứa') || 
              lowerText.includes('nhóm này chứa') || 
              lowerText.includes('khối này chứa') ||
              lowerText.includes('nhóm mã số')
             )) {
             if (text.length < 100) {
                 skipNextUl = true;
                 continue;
             }
          }

          if (tagName === 'UL' || tagName === 'OL') {
            if (skipNextUl) {
              skipNextUl = false;
              continue;
            }
            
            const lis = Array.from(el.querySelectorAll('li')).map(li => {
                return li.innerText.trim(); 
            });
            text = '\n' + lis.join('\n'); 
          } else {
            if (skipNextUl) skipNextUl = false;
          }

          if (tagName === 'DT' || el.querySelector('dt') || 
              tagName === 'B' || tagName === 'STRONG') {
             text = text.replace(/:$/, '');
             text = '\n' + text.toUpperCase() + ':'; 
          }

          fullText += text + '\n';
        }
        return fullText.trim();
      }, code, name, selector);
    } catch (e) { 
      return ""; 
    }
  }

  parseText(text) {
    if (!text) return { code: "", name: "" };
    let parts = text.includes(':') ? text.split(':', 2) : text.trim().split(' ');
    const code = parts[0].trim();
    const name = parts.length > 1 ? 
      parts.slice(1).join(' ').trim() : 
      text.replace(code, '').trim();
    return { code, name };
  }

  async crawlStructureRecursive(parentId, parentLevel) {
    const childrenNodes = await this.page.evaluate((pId, pLevel) => {
        const allNodes = Array.from(document.querySelectorAll(
          'mat-nested-tree-node, mat-tree-node'
        ));
        const pIdNoDot = pId.replace(/\./g, '');
        const parentIndex = allNodes.findIndex(node => 
          node.id === pId || node.id === pIdNoDot
        );
        if (parentIndex === -1) return [];

        const results = [];
        for (let i = parentIndex + 1; i < allNodes.length; i++) {
            const node = allNodes[i];
            const level = parseInt(node.getAttribute('aria-level'));
            if (level <= pLevel) break; 
            if (level === pLevel + 1) { 
                results.push({ 
                    id: node.id, 
                    text: node.querySelector('span.cursor-pointer')?.textContent.trim() || '',
                    level: level
                });
            }
        }
        return results;
    }, parentId, parentLevel);

    const processedChildren = [];

    for (const child of childrenNodes) {
        const { code, name } = this.parseText(child.text);
        
        let type = 'unknown';
        if (child.id.includes('-')) type = 'group';
        else if (child.id.includes('.')) type = 'sub_disease';
        else type = 'disease';

        if (type !== 'group') continue;

        console.log(`      ${"  ".repeat(child.level - 1)}↳ [${type}] ${code}`);

        const nodeData = {
            type,
            code,
            name,
            description: "",
            children: []
        };

        await this.clickNodeInTree(child.id, code);
        const desc = await this.getSmartDescription(code, name);
        if (desc) {
            nodeData.description = desc;
            console.log(`        📝 [GROUP DESC] ${code} (${desc.length} chars)`);
        }

        const expanded = await this.expandNodeInTree(child.id);
        if (expanded) {
            nodeData.children = await this.crawlStructureRecursive(child.id, child.level);
        }

        processedChildren.push(nodeData);
    }
    return processedChildren;
  }

  async crawlAll() {
    try {
      console.log('\n' + '='.repeat(80));
      console.log(`🚀 BẮT ĐẦU CRAWL CẤU TRÚC (HOÀN CHỈNH)`);
      console.log('='.repeat(80) + '\n');

      const chapters = await this.page.evaluate(() => {
        const chapterNodes = Array.from(
          document.querySelectorAll('mat-nested-tree-node, mat-tree-node')
        ).filter(node => node.getAttribute('aria-level') === '1');
        return chapterNodes.map(node => ({
          id: node.id,
          text: node.querySelector('span.cursor-pointer')?.textContent.trim() || '',
          level: 1
        }));
      });

      console.log(`✅ Tìm thấy tổng ${chapters.length} chương trên web\n`);

      const endIndex = Math.min(CONFIG.START_INDEX + CONFIG.COUNT, chapters.length);

      for (let i = CONFIG.START_INDEX; i < endIndex; i++) { 
        const chapter = chapters[i];
        const { code, name } = this.parseText(chapter.text);

        console.log(`📖 ĐANG XỬ LÝ CHƯƠNG [${i}]: ${code} - ${name}`);

        await this.clickNodeInTree(chapter.id, code);
        const description = await this.getSmartDescription(code, name);
        if (description) {
             console.log(`   📝 [CHAPTER DESC] Chương ${code} (${description.length} chars)`);
        }
        
        await this.expandNodeInTree(chapter.id);
        await this.sleep(500); 

        const childrenData = await this.crawlStructureRecursive(chapter.id, 1);

        const chapterInfo = {
          type: 'chapter',
          code,
          name,
          description,
          children: childrenData
        };

        this.data.push(chapterInfo);
        console.log(`✅ Hoàn thành cấu trúc chương ${code}\n`);
        
        await this.saveToJson();
      }
      console.log('\n🎉 DONE! Đã crawl xong toàn bộ cấu trúc!');
    } catch (error) { 
      console.error('\n❌ Lỗi:', error); 
    }
  }

  async saveToJson(filename = CONFIG.OUTPUT_FILE) {
    const absolutePath = path.resolve(filename);
    const dir = path.dirname(absolutePath);
    try { 
      await fs.mkdir(dir, { recursive: true }); 
    } catch (err) {}
    await fs.writeFile(absolutePath, JSON.stringify(this.data, null, 2), 'utf-8');
    console.log(`💾 Đã cập nhật file tại: ${absolutePath}\n`);
  }

  async close() { 
    if (this.browser) await this.browser.close(); 
  }
}

// =================================================================
// MAIN
// =================================================================
(async () => {
  const crawler = new ICD10StructureCrawler();
  try { 
    await crawler.start(); 
    await crawler.crawlAll(); 
  } catch (error) { 
    console.error('\n❌ Lỗi:', error); 
  } finally { 
    await crawler.close(); 
  }
})();