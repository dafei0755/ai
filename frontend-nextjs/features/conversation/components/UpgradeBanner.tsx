'use client';

interface UpgradeBannerProps {
  adaptiveChatGutter: string;
  onUpgradeConfirm?: () => void;
  onUpgradeDismiss?: () => void;
}

export function UpgradeBanner({
  adaptiveChatGutter,
  onUpgradeConfirm,
  onUpgradeDismiss,
}: UpgradeBannerProps) {
  return (
    <div
      className="ui-type-meta mt-3 p-3.5 bg-amber-50 border border-amber-300 rounded-xl flex items-center gap-3 flex-shrink-0"
      style={{ marginInline: adaptiveChatGutter }}
    >
      <span className="text-amber-500 text-lg flex-shrink-0">✨</span>
      <span className="text-amber-800 flex-1">
        对话已积累足够上下文，可以整理为正式项目
      </span>
      <button
        onClick={onUpgradeConfirm}
        className="ui-type-meta px-3 py-1.5 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors flex-shrink-0"
      >
        立即整理
      </button>
      <button
        onClick={onUpgradeDismiss}
        className="ui-type-meta text-amber-400 hover:text-amber-600 flex-shrink-0"
      >
        稍后
      </button>
    </div>
  );
}
