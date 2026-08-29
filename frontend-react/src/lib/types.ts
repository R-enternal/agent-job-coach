export interface Session {
  session_id: string;
  message_count: number;
  preview: string;
  updated_at: number;
}

export interface ChatMessage {
  role: "user" | "ai";
  content: string;
  tools?: string[];
}

export interface Jd {
  id: number;
  title: string;
  company: string;
  raw_text: string;
  parsed: {
    title?: string;
    company?: string;
    skills?: string[];
    experience?: string[];
    soft?: string[];
    summary?: string;
  };
  source: string;
  status: string;
}

export interface Qlist {
  id: number;
  jd_id: number | null;
  quota: Record<string, number>;
  questions: Array<{
    qtype: string;
    question: string;
    difficulty?: string;
    source?: string;
  }>;
  status: string;
  total: number;
  created_at?: string;
}

export interface InterviewRecord {
  session_id: string;
  topic: string;
  rounds: number;
  avg_score: number;
  created_at: string;
}

export interface KbDocument {
  source: string;
  category: string;
  category_name: string;
  chunks: number;
}

/** 面试三类题型（题单 quota 的 key → 展示名） */
export const QTYPE_NAMES: Record<string, string> = {
  "eight-part": "技术八股",
  project: "项目深挖",
  business: "业务场景",
};

/** 生成题单的默认配额：三类各 3 题 */
export const QLIST_QUOTA: Record<string, number> = {
  "eight-part": 3,
  project: 3,
  business: 3,
};

/** 知识库资料分类（不含 resume —— 简历走独立卡） */
export const KB_CATEGORIES: Record<string, string> = {
  project: "项目文档",
  interview: "面试题库",
  jd: "岗位JD",
  resume: "个人简历",
};

export const DIM_LABELS: Record<string, string> = {
  correctness: "正确性",
  depth: "深度",
  structure: "结构",
  expression: "表达",
  risk_awareness: "风险意识",
};

export const TOPIC_NAMES: Record<string, string> = {
  mixed: "模拟面试",
  agent: "Agent 专项",
  rag: "RAG 专项",
  project: "项目深挖",
  "eight-part": "八股基础",
  hr: "HR 面",
};
