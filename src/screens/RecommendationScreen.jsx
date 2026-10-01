import React from "react";
import RecommendationForm from "../components/recommendation/RecommendationForm.jsx";
import RecommendationResults from "../components/recommendation/RecommendationResults.jsx";
import "./recommendation.css";

export default function RecommendationScreen() {
  return (
    <div className="ai-workspace app-view" id="recommendSection">
      <RecommendationForm />
      <main className="ai-main">
        <header className="ai-page-heading">
          <h2>내게 맞는 PC, 쉽게 찾아보세요</h2>
          <p>예산과 사용 목적을 알려주시면 알맞은 구성을 추천해 드려요.</p>
        </header>
        <RecommendationResults />
      </main>
    </div>
  );
}
