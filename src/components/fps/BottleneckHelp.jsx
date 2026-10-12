import React, { useId, useState } from "react";

export default function BottleneckHelp({ component, compared, capped }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="fpr-limit-help">
      <button
        type="button"
        className="fpr-help-button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen(!open)}
      >
        <span aria-hidden="true">?</span> {component} 제한 영향이란?
      </button>
      <div id={id} hidden={!open} className="fpr-help-content">
        <p>
          {component === "CPU"
            ? "CPU는 게임의 다음 장면을 준비하는 친구예요. 준비가 늦으면 GPU도 기다려야 해요."
            : "GPU는 준비된 장면을 그림으로 그리는 친구예요. 그림을 그리는 데 오래 걸리면 화면도 늦게 바뀌어요."}
        </p>
        <p>
          {capped
            ? "지금은 게임이 정한 FPS 한도에 도달해서 양쪽을 0%로 표시해요. 부품의 성능이 같다는 뜻은 아니에요."
            : compared
              ? `이 숫자는 다른 부품은 그대로 두고 ${component}를 바꿔 테스트한 가장 빠른 PC와의 차이예요. 0%는 비교한 PC보다 느리지 않다는 뜻이에요.`
              : `이 숫자가 클수록 ${component}의 속도가 화면을 더 빠르게 만드는 데 걸림돌이 된다는 예상이에요. 0%는 지금 이 부품 때문에 느려지는 영향이 거의 없다는 뜻이에요.`}
        </p>
        <p>
          부품이 일하는 양(사용률)이 아니에요. 두 숫자를 더해 100%가 될 필요도
          없어요.
        </p>
      </div>
    </div>
  );
}
