export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "13.0.5"
  }
  public: {
    Tables: {
      course_sections: {
        Row: {
          capacity: number | null
          course_id: string | null
          days: string | null
          end_time: string | null
          enrolled: number | null
          id: string
          location: string | null
          modality: string | null
          professor_id: string | null
          professor_name: string | null
          scraped_at: string | null
          section_number: string
          start_time: string | null
          updated_at: string | null
        }
        Insert: {
          capacity?: number | null
          course_id?: string | null
          days?: string | null
          end_time?: string | null
          enrolled?: number | null
          id?: string
          location?: string | null
          modality?: string | null
          professor_id?: string | null
          professor_name?: string | null
          scraped_at?: string | null
          section_number: string
          start_time?: string | null
          updated_at?: string | null
        }
        Update: {
          capacity?: number | null
          course_id?: string | null
          days?: string | null
          end_time?: string | null
          enrolled?: number | null
          id?: string
          location?: string | null
          modality?: string | null
          professor_id?: string | null
          professor_name?: string | null
          scraped_at?: string | null
          section_number?: string
          start_time?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "course_sections_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "course_sections_professor_id_fkey"
            columns: ["professor_id"]
            isOneToOne: false
            referencedRelation: "professors"
            referencedColumns: ["id"]
          },
        ]
      }
      courses: {
        Row: {
          course_code: string
          course_number: string | null
          created_at: string | null
          credits: number | null
          department: string | null
          description: string | null
          id: string
          last_scraped: string | null
          name: string
          semester: string
          subject_code: string | null
          university: string | null
        }
        Insert: {
          course_code: string
          course_number?: string | null
          created_at?: string | null
          credits?: number | null
          department?: string | null
          description?: string | null
          id?: string
          last_scraped?: string | null
          name: string
          semester: string
          subject_code?: string | null
          university?: string | null
        }
        Update: {
          course_code?: string
          course_number?: string | null
          created_at?: string | null
          credits?: number | null
          department?: string | null
          description?: string | null
          id?: string
          last_scraped?: string | null
          name?: string
          semester?: string
          subject_code?: string | null
          university?: string | null
        }
        Relationships: []
      }
      professor_reviews: {
        Row: {
          created_at: string | null
          difficulty: number | null
          id: string
          professor_id: string | null
          rating: number | null
          review_text: string | null
          scraped_at: string | null
          sentiment_aspects: Json | null
          sentiment_positive: number | null
        }
        Insert: {
          created_at?: string | null
          difficulty?: number | null
          id?: string
          professor_id?: string | null
          rating?: number | null
          review_text?: string | null
          scraped_at?: string | null
          sentiment_aspects?: Json | null
          sentiment_positive?: number | null
        }
        Update: {
          created_at?: string | null
          difficulty?: number | null
          id?: string
          professor_id?: string | null
          rating?: number | null
          review_text?: string | null
          scraped_at?: string | null
          sentiment_aspects?: Json | null
          sentiment_positive?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "professor_reviews_professor_id_fkey"
            columns: ["professor_id"]
            isOneToOne: false
            referencedRelation: "professors"
            referencedColumns: ["id"]
          },
        ]
      }
      professors: {
        Row: {
          average_difficulty: number | null
          average_rating: number | null
          composite_score: number | null
          created_at: string | null
          department: string | null
          grade_letter: string | null
          id: string
          last_updated: string | null
          name: string
          ratemyprof_id: string | null
          review_count: number | null
          university: string | null
        }
        Insert: {
          average_difficulty?: number | null
          average_rating?: number | null
          composite_score?: number | null
          created_at?: string | null
          department?: string | null
          grade_letter?: string | null
          id?: string
          last_updated?: string | null
          name: string
          ratemyprof_id?: string | null
          review_count?: number | null
          university?: string | null
        }
        Update: {
          average_difficulty?: number | null
          average_rating?: number | null
          composite_score?: number | null
          created_at?: string | null
          department?: string | null
          grade_letter?: string | null
          id?: string
          last_updated?: string | null
          name?: string
          ratemyprof_id?: string | null
          review_count?: number | null
          university?: string | null
        }
        Relationships: []
      }
      user_schedules: {
        Row: {
          created_at: string | null
          id: string
          name: string | null
          sections: string[] | null
          semester: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string | null
          id?: string
          name?: string | null
          sections?: string[] | null
          semester?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string | null
          id?: string
          name?: string | null
          sections?: string[] | null
          semester?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "user_schedules_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      users: {
        Row: {
          created_at: string | null
          email: string
          graduation_year: number | null
          id: string
          major: string | null
          name: string | null
          preferences: Json | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          email: string
          graduation_year?: number | null
          id?: string
          major?: string | null
          name?: string | null
          preferences?: Json | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          email?: string
          graduation_year?: number | null
          id?: string
          major?: string | null
          name?: string | null
          preferences?: Json | null
          updated_at?: string | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
