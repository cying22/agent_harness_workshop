const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "Agent Harness Workshop";
pres.title = "Workshop 设计";

// Color palette (warm copper/terracotta)
const C = {
  bg: "141414",
  bgCard: "252020",
  bgCardAlt: "1A1A1A",
  border: "3D3330",
  white: "FFFFFF",
  text: "D4CCC4",
  muted: "9C9088",
  copper: "C8956C",
  copperLight: "D4A574",
};

// ============ Slide 1: 核心理念 ============
let s1 = pres.addSlide();
s1.background = { color: C.bg };

// Left accent bar
s1.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 0.5, w: 0.04, h: 1.2, fill: { color: C.copper } });

// Title
s1.addText("Workshop 设计", {
  x: 0.65, y: 0.5, w: 8, h: 0.7,
  fontSize: 36, fontFace: "Microsoft YaHei", bold: true, color: C.white, margin: 0,
});

// Subtitle
s1.addText("核心理念：痛点驱动的递进建造 — 6 Lab 对齐 6 层架构", {
  x: 0.65, y: 1.2, w: 8, h: 0.4,
  fontSize: 14, fontFace: "Microsoft YaHei", color: C.copper, margin: 0,
});

// Description
s1.addText("不是讲理论，而是让你亲手从零搭建一个 Mini Harness。6 个 Lab 分别对应 Harness 六层核心组件，每个 Lab 暴露一个真实痛点，然后用一层 Harness 解决它。", {
  x: 0.65, y: 1.75, w: 8.5, h: 0.6,
  fontSize: 12, fontFace: "Microsoft YaHei", color: C.muted, margin: 0,
});

// Flow diagram - 6 steps
const labs = [
  { num: "Lab 1", layer: "提示与引导层", pain: "裸 LLM 无规则，行为混乱", arrow: "有了引导，但说了做不了" },
  { num: "Lab 2", layer: "工具与执行层", pain: "能做了，但不安全", arrow: "能执行，但没有安全检查" },
  { num: "Lab 3", layer: "验证与安全层", pain: "安全了，但长对话爆 token", arrow: "安全了，但记忆有限" },
  { num: "Lab 4", layer: "上下文与内存层", pain: "记忆管好了，但复杂任务忙不过来", arrow: "能记忆，但无法分工" },
  { num: "Lab 5", layer: "规划与协调层", pain: "能协作了，但关掉就丢失一切", arrow: "能协作，但无法持久" },
  { num: "Lab 6", layer: "状态与持久层", pain: "完整 Mini Harness", arrow: "" },
];

const startY = 2.55;
const stepH = 0.42;
const gap = 0.08;

labs.forEach((lab, i) => {
  const y = startY + i * (stepH + gap);

  // Number circle
  s1.addShape(pres.shapes.OVAL, {
    x: 0.65, y: y + 0.02, w: 0.36, h: 0.36,
    fill: { color: C.copper },
  });
  s1.addText(String(i + 1), {
    x: 0.65, y: y + 0.02, w: 0.36, h: 0.36,
    fontSize: 12, fontFace: "JetBrains Mono", bold: true, color: C.bg, align: "center", valign: "middle", margin: 0,
  });

  // Connector line (except last)
  if (i < 5) {
    s1.addShape(pres.shapes.RECTANGLE, {
      x: 0.82, y: y + 0.38, w: 0.02, h: gap + 0.04,
      fill: { color: C.border },
    });
  }

  // Layer name
  s1.addText(lab.layer, {
    x: 1.15, y: y, w: 1.8, h: stepH,
    fontSize: 11, fontFace: "Microsoft YaHei", bold: true, color: C.white, valign: "middle", margin: 0,
  });

  // Pain point
  s1.addText([
    { text: "痛点  ", options: { fontSize: 10, color: C.copper, bold: true } },
    { text: lab.pain, options: { fontSize: 10, color: C.muted } },
  ], {
    x: 3.1, y: y, w: 4.5, h: stepH, valign: "middle", margin: 0,
  });

  // Check mark for last
  if (i === 5) {
    s1.addText("✅", {
      x: 7.7, y: y, w: 0.4, h: stepH, fontSize: 14, valign: "middle", margin: 0,
    });
  }

  // Arrow text (right side)
  if (lab.arrow && i < 5) {
    s1.addText("→ " + lab.arrow, {
      x: 7.8, y: y, w: 2, h: stepH,
      fontSize: 8, fontFace: "Microsoft YaHei", color: C.border, valign: "middle", margin: 0,
    });
  }
});


// ============ Slide 2: 六个实验模块 ============
let s2 = pres.addSlide();
s2.background = { color: C.bg };

// Title
s2.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 0.4, w: 0.04, h: 0.7, fill: { color: C.copper } });
s2.addText("六个实验模块", {
  x: 0.65, y: 0.4, w: 6, h: 0.45,
  fontSize: 28, fontFace: "Microsoft YaHei", bold: true, color: C.white, margin: 0,
});
s2.addText("每个 Lab 对齐一层 Harness 架构，附带 Claude Code 源码参考", {
  x: 0.65, y: 0.88, w: 8, h: 0.3,
  fontSize: 11, fontFace: "Microsoft YaHei", color: C.muted, margin: 0,
});

// Table data
const tableRows = [
  ["Lab", "Harness 层级", "你将实现", "对应 Claude Code 源码", "时间"],
  ["1", "提示与引导层", "System prompt 工程 + CLAUDE.md + Hooks", "QueryEngine.ts, memdir/, hooks", "30min"],
  ["2", "工具与执行层", "统一 Tool 接口 + 3 个工具 + 执行管道", "Tool.ts, BashTool/", "35min"],
  ["3", "验证与安全层", "权限中间件 + Bash 分类器 + HITL", "permissions/, bashClassifier", "30min"],
  ["4", "上下文与内存层", "Micro-compaction + 项目记忆", "apiMicrocompact.ts, memdir/", "25min"],
  ["5", "规划与协调层", "AgentTool + 任务管理", "AgentTool/, TaskCreateTool/", "25min"],
  ["6", "状态与持久层", "Session 持久化 + Resume + Rewind", "session persistence, /resume", "20min"],
];

s2.addTable(tableRows, {
  x: 0.5, y: 1.4, w: 9.0,
  fontSize: 10,
  fontFace: "Microsoft YaHei",
  color: C.text,
  border: { type: "solid", pt: 0.5, color: C.border },
  colW: [0.5, 1.4, 2.8, 2.5, 0.7],
  rowH: [0.4, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45],
  autoPage: false,
  headerRow: true,
  headerRowBgColor: C.bgCard,
  headerRowColor: C.copper,
  headerRowFontSize: 9,
  headerRowFontBold: true,
  altRowBgColor: [C.bg, C.bgCardAlt],
});

// ============ Slide 3: Lab 结构 + 总结 ============
let s3 = pres.addSlide();
s3.background = { color: C.bg };

// Title
s3.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 0.4, w: 0.04, h: 0.7, fill: { color: C.copper } });
s3.addText("每个 Lab 的结构", {
  x: 0.65, y: 0.4, w: 6, h: 0.45,
  fontSize: 28, fontFace: "Microsoft YaHei", bold: true, color: C.white, margin: 0,
});
s3.addText("四步闭环，从痛点到验证", {
  x: 0.65, y: 0.88, w: 8, h: 0.3,
  fontSize: 11, fontFace: "Microsoft YaHei", color: C.muted, margin: 0,
});

// Four steps
const steps = [
  { num: "01", title: "痛点演示", time: "5 min", desc: "运行上一个 Lab 的代码，碰到天花板" },
  { num: "02", title: "源码对照", time: "5 min", desc: "对照 Claude Code 中的真实设计" },
  { num: "03", title: "动手编码", time: "20-30 min", desc: "用 Python 写这一层的简化实现" },
  { num: "04", title: "验证运行", time: "5 min", desc: "运行增强后的 agent，确认问题解决" },
];

steps.forEach((step, i) => {
  const cardX = 0.5 + i * 2.3;
  const cardY = 1.5;
  const cardW = 2.1;
  const cardH = 2.2;

  // Card background
  s3.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: cardX, y: cardY, w: cardW, h: cardH,
    fill: { color: C.bgCardAlt },
    line: { color: C.border, width: 0.75 },
    rectRadius: 0.1,
  });

  // Step number
  s3.addShape(pres.shapes.OVAL, {
    x: cardX + 0.7, y: cardY + 0.25, w: 0.55, h: 0.55,
    fill: { color: C.copper },
  });
  s3.addText(step.num, {
    x: cardX + 0.7, y: cardY + 0.25, w: 0.55, h: 0.55,
    fontSize: 16, fontFace: "JetBrains Mono", bold: true, color: C.bg, align: "center", valign: "middle", margin: 0,
  });

  // Title
  s3.addText(step.title, {
    x: cardX + 0.15, y: cardY + 1.0, w: cardW - 0.3, h: 0.35,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true, color: C.white, align: "center", margin: 0,
  });

  // Time badge
  s3.addText(step.time, {
    x: cardX + 0.5, y: cardY + 1.35, w: cardW - 1.0, h: 0.25,
    fontSize: 10, fontFace: "JetBrains Mono", color: C.copper, align: "center", margin: 0,
  });

  // Description
  s3.addText(step.desc, {
    x: cardX + 0.15, y: cardY + 1.65, w: cardW - 0.3, h: 0.4,
    fontSize: 10, fontFace: "Microsoft YaHei", color: C.muted, align: "center", valign: "top", margin: 0,
  });

  // Arrow between cards (except last)
  if (i < 3) {
    s3.addText("→", {
      x: cardX + cardW, y: cardY + 0.7, w: 0.2, h: 0.5,
      fontSize: 16, color: C.copper, align: "center", valign: "middle", margin: 0,
    });
  }
});

// Bottom callout
s3.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.5, y: 4.1, w: 9.0, h: 0.95,
  fill: { color: "1A1210" },
  line: { color: C.copper, width: 0, type: "none" },
  rectRadius: 0.08,
});
// Left accent border
s3.addShape(pres.shapes.RECTANGLE, {
  x: 0.5, y: 4.1, w: 0.04, h: 0.95,
  fill: { color: C.copper },
});

s3.addText([
  { text: "环境要求  ", options: { bold: true, color: C.white, fontSize: 12 } },
  { text: "Python 3.11+  |  AWS 账户（Amazon Bedrock）  |  Jupyter Notebook", options: { color: C.muted, fontSize: 11 } },
  { text: "\n快速开始  ", options: { bold: true, color: C.white, fontSize: 12, breakLine: true } },
  { text: "cd labs/ → pip install -r requirements.txt → jupyter notebook → 按顺序打开 lab1 ~ lab6", options: { color: C.muted, fontSize: 11 } },
], {
  x: 0.75, y: 4.15, w: 8.5, h: 0.85,
  fontFace: "Microsoft YaHei", valign: "middle",
});


// Write file
pres.writeFile({ fileName: "/home/ubuntu/workspace/agent_harness/workshop_design.pptx" })
  .then(() => console.log("Created workshop_design.pptx"))
  .catch(err => console.error(err));
