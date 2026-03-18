export interface Category {
  id: string
  name: string
  gromo_category_id: string | null
  is_excluded: boolean
  synced_at: string | null
  created_at: string
  product_count: number
}

export interface Product {
  id: string
  category_id: string
  category_name: string
  name: string
  gromo_product_id: string | null
  description: string | null
  features: Record<string, unknown> | null
  eligibility: Record<string, unknown> | null
  fees: Record<string, unknown> | null
  benefits: Record<string, unknown> | null
  faqs: Record<string, unknown> | null
  synced_at: string | null
  created_at: string
}

export interface Avatar {
  id: string
  name: string
  image_path: string
  is_default: boolean
  created_at: string
}

export interface Voice {
  id: string
  name: string
  sample_path: string
  language: string
  is_default: boolean
  created_at: string
}

export type JobType = 'single_product' | 'category_overview' | 'comparison' | 'ppt_mode'
export type JobStatus = 'queued' | 'generating_script' | 'generating_audio' | 'generating_avatar' | 'compositing' | 'completed' | 'failed'
export type Difficulty = 'easy' | 'medium' | 'hard'

export interface VideoJob {
  id: string
  title: string
  job_type: JobType
  product_ids: string[] | null
  avatar_id: string | null
  voice_id: string | null
  language: string
  status: JobStatus
  progress: number
  script_text: string | null
  audio_path: string | null
  video_path: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface RoleplaySession {
  id: string
  product_id: string
  difficulty: Difficulty
  conversation_log: Record<string, unknown> | null
  overall_score: number | null
  skill_scores: Record<string, number> | null
  feedback: string | null
  duration_seconds: number | null
  created_at: string
}
