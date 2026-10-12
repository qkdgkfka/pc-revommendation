import React from "react";
import RecommendationForm from "../components/recommendation/RecommendationForm.jsx";
import RecommendationResults from "../components/recommendation/RecommendationResults.jsx";
import { PageHeading } from "../components/Controls.jsx";
import "./recommendation.css";

export default function RecommendationScreen() {
  return (
    <main className="app-view" id="recommendSection">
      <PageHeading title="내게 맞는 PC, 쉽게 찾아보세요">
        예산과 사용 목적을 알려주시면 알맞은 구성을 추천해 드려요.
      </PageHeading>
      <div className="ai-workspace">
        <RecommendationForm />
        <RecommendationResults />
      </div>
    </main>
  );
}
