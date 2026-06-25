<!-- 第四步：最终回复 + 模拟推演 -->
<template>
  <div class="final-result">
    <!-- 最终回复 -->
    <h2>✅ 最终回复</h2>
    <div class="final-reply-box">
      <p>{{ finalReply }}</p>
      <span class="copy-hint">👆 可直接复制发送给对方</span>
    </div>

    <!-- 模拟推演 -->
    <h2 style="margin-top: 32px;">🔮 对方反应模拟剧本</h2>
    <div v-if="simulation" class="sim-grid">
      <div class="sim-card sim-best">
        <div class="sim-label">🟢 最佳情况</div>
        <p>{{ simulation.best_case }}</p>
      </div>
      <div class="sim-card sim-normal">
        <div class="sim-label">🟡 一般情况</div>
        <p>{{ simulation.normal_case }}</p>
      </div>
      <div class="sim-card sim-worst">
        <div class="sim-label">🔴 最差情况</div>
        <p>{{ simulation.worst_case }}</p>
        <div v-if="simulation.fallback_suggestion" class="fallback">
          🆘 <strong>补救建议：</strong>{{ simulation.fallback_suggestion }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  finalReply: { type: String, default: '' },
  simulation: { type: Object, default: null },
})
</script>

<style scoped>
.final-result { margin-top: 24px; }
.final-reply-box {
  background: linear-gradient(135deg, #fce7f3, #fdf2f8);
  border: 2px solid #e91e63; border-radius: 12px; padding: 24px;
  text-align: center; margin-top: 12px;
}
.final-reply-box p { font-size: 22px; font-weight: 600; color: #831843; margin: 0 0 8px; }
.copy-hint { font-size: 12px; color: #9ca3af; }
.sim-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 12px; }
.sim-card {
  background: #fff; border-radius: 12px; padding: 20px; border: 1px solid #eee;
}
.sim-label { font-weight: 600; margin-bottom: 10px; font-size: 14px; }
.sim-card p { color: #444; line-height: 1.6; font-size: 14px; }
.sim-best { border-top: 3px solid #22c55e; }
.sim-normal { border-top: 3px solid #f59e0b; }
.sim-worst { border-top: 3px solid #ef4444; }
.fallback {
  margin-top: 14px; padding-top: 14px; border-top: 1px solid #f3f4f6;
  font-size: 13px; color: #666; line-height: 1.6;
}
</style>
