export type Topic = "chat" | "coding" | "automation";
export type Level = "beginner" | "intermediate" | "advanced";

export interface Rank {
  name: string;
  xp: number;
  floor: number;
  next_name: string | null;
  next_xp: number | null;
}

export interface User {
  id: number;
  name: string;
  email: string | null;
  avatar_url: string | null;
  telegram_id: number | null;
  telegram_username: string | null;
  registered: boolean;
  topics: Topic[];
  daily_count: number;
  notify: boolean;
  level: Level;
  level_name: string;
  xp: number;
  rank: Rank;
  is_admin: boolean;
}

export interface Meta {
  app_name: string;
  topics: { key: Topic; name: string }[];
  levels: { key: Level; name: string }[];
  google_client_id: string;
  bot_username: string;
  daily_hour: number;
  daily_min: number;
  daily_max: number;
}

export interface Progress {
  sent: boolean;
  read: boolean;
  done: boolean;
  quiz_score: number | null;
  quiz_total: number | null;
}

export interface QuizQuestion {
  q: string;
  options: string[];
  answer?: number;
  explain?: string;
}

export interface Lesson {
  id: number;
  slug: string;
  title: string;
  topic: Topic;
  topic_name: string;
  tool: string;
  level: Level;
  level_name: string;
  minutes: number;
  importance: number;
  summary: string;
  source_url: string;
  origin: "news" | "on_demand" | "manual";
  status: "draft" | "published" | "rejected";
  published_at: string | null;
  created_at: string | null;
  quiz_count: number;
  progress: Progress;
}

export interface LessonFull extends Lesson {
  body_md: string;
  task_md: string;
  quiz: QuizQuestion[];
  related?: Lesson[];
  stats?: { sent: number; read: number; done: number };
}

export interface Paged<T> {
  total: number;
  page?: number;
  size?: number;
  items: T[];
}

export interface Review {
  id: number;
  lesson: { title: string; slug: string };
  question: string;
  options: string[];
}

export interface Achievement {
  key: string;
  icon: string;
  name: string;
  desc: string;
  earned: boolean;
}

export interface Stats {
  read: number;
  done: number;
  received: number;
  streak: number;
  best_streak: number;
  quizzes: number;
  quiz_accuracy: number;
  perfect_quizzes: number;
  reviews_done: number;
  reviews_due: number;
  by_topic: { key: Topic; name: string; done: number; total: number }[];
  week: { day: string; done: number; read: number }[];
  level: Level;
  level_name: string;
  rank: Rank;
  achievements: Achievement[];
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string | null;
}

export interface QuizResult {
  score: number;
  total: number;
  results: { correct: boolean; answer: number; given: number; explain: string }[];
  xp: number;
  level_changed: Level | null;
  user_xp: number;
  user_level: Level;
}
