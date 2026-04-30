import re

with open(r'app\analysis\[sessionId]\page.tsx', encoding='utf-8') as f:
    content = f.read()

old = (
    '\t\t\t\t\t\t\t\t\t\t\t{currentProgressiveStep > 0 ? (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t<UnifiedProgressiveQuestionnaireModal\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tinline={true}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tisOpen={true}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tcurrentStep={currentProgressiveStep}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tstepData={progressiveStepData}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tonConfirm={handleProgressiveStepConfirm}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tonSkip={handleProgressiveStepSkip}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tsessionId={sessionId as string}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tuserInput={userInput}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t/>\n'
    '\t\t\t\t\t\t\t\t\t\t\t) : showRoleTaskReview ? ('
)

new = (
    '\t\t\t\t\t\t\t\t\t\t\t{currentProgressiveStep === 1 ? (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t// 意图确认 → 简化为AI聊天气泡，AI推荐值一键确认，无需填表\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex items-start gap-2">\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex-1 bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl rounded-bl-sm p-4 space-y-3">\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t{progressiveStepData?.requirements_review?.breakthrough_insight && (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<p className="text-sm text-[var(--foreground)] leading-relaxed italic">\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t&ldquo;{progressiveStepData.requirements_review.breakthrough_insight}&rdquo;\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</p>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t)}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t{(() => {\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tconst deliveries: any[] = (progressiveStepData?.delivery_types?.options ?? []).filter((o: any) => o.recommended);\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tif (!deliveries.length) return null;\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\treturn (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<p className="text-xs text-[var(--foreground-secondary)] mb-1.5">建议输出：</p>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex flex-wrap gap-1.5">\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t{deliveries.map((o: any) => (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<span key={o.id} className="px-2.5 py-1 text-xs rounded-full bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30">{o.label}</span>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t))}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t);\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t})()}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t<div className="flex gap-2 pt-1">\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<button\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tonClick={() => {\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tconst dOpts: any[] = progressiveStepData?.delivery_types?.options ?? [];\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tconst mOpts: any[] = progressiveStepData?.identity_modes?.options ?? [];\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tconst cOpts: any[] = progressiveStepData?.recommended_constraints?.options ?? [];\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\thandleProgressiveStepConfirm({\n'
    "\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tselected_deliveries: dOpts.filter((o: any) => o.recommended).map((o: any) => o.id),\n"
    "\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tselected_modes: mOpts.filter((o: any) => o.recommended).map((o: any) => o.id),\n"
    "\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tconfirmed_constraints: cOpts.filter((o: any) => o.recommended).map((o: any) => ({ id: o.id, label: o.label, desc: o.desc, source: 'ai_recommended' })),\n"
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t});\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t}}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\tclassName="px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg text-sm transition-colors font-medium flex items-center gap-1.5"\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<CheckCircle2 className="w-4 h-4" />\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t确认，开始分析\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t</button>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\t</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t</div>\n'
    '\t\t\t\t\t\t\t\t\t\t\t) : currentProgressiveStep > 1 ? (\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t<UnifiedProgressiveQuestionnaireModal\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tinline={true}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tisOpen={true}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tcurrentStep={currentProgressiveStep}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tstepData={progressiveStepData}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tonConfirm={handleProgressiveStepConfirm}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tonSkip={handleProgressiveStepSkip}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tsessionId={sessionId as string}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t\tuserInput={userInput}\n'
    '\t\t\t\t\t\t\t\t\t\t\t\t/>\n'
    '\t\t\t\t\t\t\t\t\t\t\t) : showRoleTaskReview ? ('
)

if old in content:
    content = content.replace(old, new, 1)
    with open(r'app\analysis\[sessionId]\page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('NOT FOUND')
    idx = content.find('currentProgressiveStep > 0 ? (')
    print(repr(content[idx-5:idx+50]))
