import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type { LLMConfig, LLMConfigUpdate, LLMTestRequest, LLMTestResponse } from '@/types'
import { toast } from 'sonner'

const KEY = ['llm-config']

export function useLLMConfig() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const { data } = await api.get<LLMConfig>('/settings/llm')
      return data
    },
  })
}

export function useUpdateLLMConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (config: LLMConfigUpdate) => {
      const { data } = await api.put<LLMConfig>('/settings/llm', config)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: KEY })
      toast.success('LLM configuration saved successfully')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to save LLM configuration')
    },
  })
}

export function useTestLLMConnection() {
  return useMutation({
    mutationFn: async (request: LLMTestRequest) => {
      const { data } = await api.post<LLMTestResponse>('/settings/llm/test', request)
      return data
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message)
      } else {
        toast.error(data.message)
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to test connection')
    },
  })
}
