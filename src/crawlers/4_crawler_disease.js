const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

// ==================================================================
// ⚙️ CONFIGURATION (DISEASE DETAIL)
// ==================================================================
const CONFIG = {
    START_INDEX: 0, 
    COUNT: 22, 
    OUTPUT_FILE: '../../data/icd10_diseases_raw.json',
    
    // Timeout
    DELAY_AFTER_CLICK: 2000, 
    DELAY_AFTER_EXPAND: 3000 
};
// ==================================================================

class ICD10DiseaseCrawler {
  constructor() {
    this.browser = null;
    this.page = null;
    this.data = [];
  }

  async start() {
    console.log('🚀 [DISEASE DETAIL] Starting browser...');
    this.browser = await puppeteer.launch({
      headless: false,
      args: ['--start-maximized', '--no-sandbox'],
      defaultViewport: null
    });

    this.page = await this.browser.newPage();
    await this.page.setViewport({ width: 1920, height: 1080 });

    console.log('📡 Accessing website...');
    await this.page.goto('https://icd.kcb.vn/icd-10/icd10', {
      waitUntil: 'networkidle2',
      timeout: 60000
    });

    await this.page.waitForSelector('mat-tree[role="tree"]', { timeout: 30000 });
    await this.sleep(3000);
    console.log('✅ Website loaded!\n');
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // =================================================================
  // 1. LOGIC CLICK & WAIT
  // =================================================================
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
      
      // Get old content
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
      
      // Wait for load: Text changed AND contains disease code
      try {
          await this.page.waitForFunction(
              (oldContent, sel, code) => {
                  const container = document.querySelector(sel);
                  if (!container) return false;
                  const newContent = container.innerText.trim();
                  // Important: Must contain disease code (code) to be considered loaded
                  return newContent !== oldContent && newContent.includes(code);
              },
              { timeout: 8000 }, oldText, contentSelector, nodeCode
          );
      } catch (e) { }
      
      await this.sleep(500); 
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
        return node.querySelector('button.mattreenodetoggle') || node.querySelector('button[aria-label*="Toggle"]');
      }, selector);

      if (toggleButton && await toggleButton.evaluate(btn => btn !== null)) {
        await toggleButton.click();
        await this.sleep(CONFIG.DELAY_AFTER_EXPAND);
        return true;
      }
      return false;
    } catch (e) { return false; }
  }

  // =================================================================
  // 2. LOGIC GET DISEASE DESCRIPTION (GET ALL - RAW)
  // =================================================================
  async getDiseaseRawDescription(code, name) {
    try {
      const selector = '.block-chapter, .block-disease, .block-type, .block-section';
      const hasContent = await this.page.waitForSelector(selector, { timeout: 2000 }).catch(() => false);
      if (!hasContent) return "";

      return await this.page.evaluate((targetCode, targetName, sel) => {
        const container = document.querySelector(sel);
        if (!container) return "";

        // Double check
        if (!container.innerText.includes(targetCode)) return "";

        let fullText = "";
        const clean = (str) => str.replace(/\s+/g, ' ').trim().toLowerCase();
        const targetStr = clean(`${targetCode} ${targetName}`);

        const children = Array.from(container.children);

        for (const el of children) {
          let text = el.innerText.trim();
          if (!text) continue;

          // 1. SKIP HEADER
          if (el.classList.contains('chapter') || el.classList.contains('section') || el.classList.contains('type')) {
              continue;
          }

          // 2. SKIP DUPLICATE TITLE
          const elTextClean = clean(text);
          if (elTextClean === targetStr || elTextClean === clean(targetCode) || elTextClean === clean(targetName)) {
              continue;
          }

          // 3. GET ALL THE REST
          const tagName = el.tagName;
          if (tagName === 'DT' || el.querySelector('b') || el.querySelector('strong')) {
               if (text.length < 100) text = `\n• ${text}`; 
          }
          
          fullText += text + '\n\n';
        }
        return fullText.trim();
      }, code, name, selector);
    } catch (e) { return ""; }
  }

  parseText(text) {
    if (!text) return { code: "", name: "" };
    let parts = text.includes(':') ? text.split(':', 2) : text.trim().split(' ');
    const code = parts[0].trim();
    const name = parts.length > 1 ? parts.slice(1).join(' ').trim() : text.replace(code, '').trim();
    return { code, name };
  }

  // =================================================================
  // 3. LOGIC CRAWL: SKIP GROUP, FOCUS ON DISEASE
  // =================================================================
  async crawlDiseaseRecursive(parentId, parentLevel) {
    // Get child list
    const childrenNodes = await this.page.evaluate((pId, pLevel) => {
        const allNodes = Array.from(document.querySelectorAll('mat-nested-tree-node, mat-tree-node'));
        const pIdNoDot = pId.replace(/\./g, '');
        const parentIndex = allNodes.findIndex(node => node.id === pId || node.id === pIdNoDot);
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
        
        // Determine type
        let type = 'unknown';
        if (child.id.includes('-')) type = 'group';
        else if (child.id.includes('.')) type = 'sub_disease';
        else type = 'disease'; // A00, G00...

        console.log(`      ${"  ".repeat(child.level - 1)}↳ [${type}] ${code}`);

        const nodeData = {
            type,
            code,
            name,
            // description: "", 
            // children: []
        };

        // --- CASE 1: GROUP ---
        if (type === 'group') {
             // Only Expand to go deeper
             const expanded = await this.expandNodeInTree(child.id);
             if (expanded) {
                 nodeData.children = await this.crawlDiseaseRecursive(child.id, child.level);
             }
        } 
        // --- CASE 2: DISEASE ---
        else if (type === 'disease') {
             // 1. Click
             await this.clickNodeInTree(child.id, code);
             
             // 2. Get RAW Description
             const rawDesc = await this.getDiseaseRawDescription(code, name);
             if (rawDesc) {
                 nodeData.description = rawDesc;
                 console.log(`        📝 [RAW DATA] ${code} (${rawDesc.length} chars)`);
             }
             
             // 3. STOP RECURSION
        }

        processedChildren.push(nodeData);
    }

    return processedChildren;
  }

  async crawlAll() {
    try {
      console.log('\n' + '='.repeat(80));
      console.log(`🚀 START CRAWLING DISEASE DETAIL`);
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

      const endIndex = Math.min(CONFIG.START_INDEX + CONFIG.COUNT, chapters.length);

      for (let i = CONFIG.START_INDEX; i < endIndex; i++) { 
        const chapter = chapters[i];
        const { code, name } = this.parseText(chapter.text);

        console.log(`📖 PROCESSING CHAPTER [${i}]: ${code} - ${name}`);

        // 1. Expand Chapter (No need description)
        await this.expandNodeInTree(chapter.id);
        await this.sleep(500); 

        // 2. Go find diseases
        const childrenData = await this.crawlDiseaseRecursive(chapter.id, 1);

        const chapterInfo = {
          type: 'chapter',
          code,
          name,
          children: childrenData
        };

        this.data.push(chapterInfo);
        console.log(`✅ Finished detail for chapter ${code}`);
        
        await this.saveToJson();
      }
      console.log('\n🎉 DONE!');
    } catch (error) { console.error(error); }
  }

  async saveToJson(filename = CONFIG.OUTPUT_FILE) {
    const absolutePath = path.resolve(filename);
    const dir = path.dirname(absolutePath);
    try { await fs.mkdir(dir, { recursive: true }); } catch (err) {}
    await fs.writeFile(absolutePath, JSON.stringify(this.data, null, 2), 'utf-8');
    console.log(`💾 Updated file at: ${absolutePath}\n`);
  }

  async close() { if (this.browser) await this.browser.close(); }
}

(async () => {
  const crawler = new ICD10DiseaseCrawler();
  try { await crawler.start(); await crawler.crawlAll(); } 
  catch (error) { console.error('\n❌ Error:', error); } 
  finally { await crawler.close(); }
})();