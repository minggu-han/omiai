<!-- 第二步：分析报告展示组件 -->
<template>
  <div class="analysis-report">
    <h2>📊 第二步：分析报告</h2>

    <div class="report-grid">
      <div class="card">
        <div class="card-title">情绪分数</div>
        <div class="score-ring" :class="scoreClass">{{ scorePercent }}</div>
        <div class="score-label">{{ scoreLabel }}</div>
      </div>

      <div class="card">
        <div class="card-title">对方意图</div>
        <div class="intent-text">{{ report.intent || 'N/A' }}</div>
        <div class="risk">
          危险等级：<span :class="'risk-' + (report.risk_level || '低')">{{ report.risk_level || 'N/A' }}</span>
        </div>
      </div>

      <div class="card insight-card">
        <div class="card-title">💡 关键洞察</div>
        <p>{{ report.key_insight || '' }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
})

const scorePercent = computed(() => {
  const s = props.report.emotion_score ?? 0.5
  return Math.round(s * 100) + '%'
})

const scoreClass = computed(() => {
  const s = props.report.emotion_score ?? 0.5
  if (s >= 0.7) return 'score-high'
  if (s >= 0.4) return 'score-mid'
  return 'score-low'
})

const scoreLabel = computed(() => {
  const s = props.report.emotion_score ?? 0.5
  if (s >= 0.7) return '对方情绪偏正向 😊'
  if (s >= 0.4) return '对方情绪中性 😐'
  return '对方情绪偏冷淡 😞'
})
</script>

<style scoped>
.analysis-report { margin-top: 24px; }
h2 { margin-bottom: 16px; }
.report-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.card {
  background: #fff; border-radius: 12px; padding: 20px;
  border: 1px solid #eee; text-align: center;
}
.card-title { font-size: 14px; color: #888; margin-bottom: 10px; }
.score-ring {
  width: 72px; height: 72px; border-radius: 50%; margin: 0 auto 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 700; color: #fff;
}
.score-high { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.score-mid  { background: linear-gradient(135deg, #f5af19, #f12711); }
.score-low  { background: linear-gradient(135deg, #f12711, #f5af19); }
.score-label { font-size: 13px; color: #666; }
.intent-text { font-size: 24px; font-weight: 600; margin: 8px 0; }
.risk { font-size: 14px; color: #888; margin-top: 8px; }
.risk-低 { color: #22c55e; font-weight: 600; }
.risk-中 { color: #f59e0b; font-weight: 600; }
.risk-高 { color: #ef4444; font-weight: 600; }
.insight-card { text-align: left; }
.insight-card p { color: #444; line-height: 1.7; font-size: 14px; }
</style>
