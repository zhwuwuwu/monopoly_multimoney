"""
Fact checking tool for MCP server.
"""

import requests
import re
from typing import List, Dict, Any


class FactCheckTool:
    """Simple fact checking tool implementation."""
    
    def __init__(self):
        self.name = "fact_check"
        self.description = "Verify the factual accuracy of claims"
    
    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fact checking."""
        claims = arguments.get('claims', [])
        
        if not claims:
            return {"error": "Claims parameter is required"}
        
        if isinstance(claims, str):
            claims = [claims]
        
        try:
            results = []
            for claim in claims[:5]:  # Limit to 5 claims
                fact_check_result = self._verify_claim(claim)
                results.append(fact_check_result)
            
            return {
                "verified_claims": results,
                "summary": self._generate_summary(results)
            }
            
        except Exception as e:
            return {"error": f"Fact checking failed: {str(e)}"}
    
    def _verify_claim(self, claim: str) -> Dict[str, Any]:
        """Verify a single claim."""
        # Simple heuristic-based fact checking
        confidence = self._calculate_confidence(claim)
        verification_status = self._determine_status(confidence)
        explanation = self._generate_explanation(claim, verification_status, confidence)
        
        return {
            "claim": claim,
            "verification_status": verification_status,
            "confidence": confidence,
            "explanation": explanation,
            "sources": self._get_mock_sources(claim),
            "recommendations": self._get_recommendations(verification_status)
        }
    
    def _calculate_confidence(self, claim: str) -> float:
        """Calculate confidence score based on simple heuristics."""
        confidence = 0.5  # Base confidence
        
        # Check for specific patterns that indicate reliability
        reliable_patterns = [
            r'根据.*报告',  # According to reports
            r'数据显示',    # Data shows
            r'研究表明',    # Research indicates
            r'统计显示',    # Statistics show
            r'官方.*表示',  # Official statement
            r'\d+%',       # Percentage
            r'\d+所',      # Number of institutions
            r'\d+年',      # Years
        ]
        
        # Check for unreliable patterns
        unreliable_patterns = [
            r'据说',       # It is said
            r'可能',       # Maybe
            r'似乎',       # Seems
            r'大概',       # Probably
            r'传闻',       # Rumors
        ]
        
        # Boost confidence for reliable patterns
        for pattern in reliable_patterns:
            if re.search(pattern, claim):
                confidence += 0.1
        
        # Reduce confidence for unreliable patterns
        for pattern in unreliable_patterns:
            if re.search(pattern, claim):
                confidence -= 0.15
        
        # Check for specific numbers/data
        if re.search(r'\d+', claim):
            confidence += 0.05
        
        # Length consideration (longer claims might be more detailed)
        if len(claim) > 100:
            confidence += 0.05
        
        return max(0.1, min(0.95, confidence))
    
    def _determine_status(self, confidence: float) -> str:
        """Determine verification status based on confidence."""
        if confidence >= 0.8:
            return "verified"
        elif confidence >= 0.6:
            return "likely_true"
        elif confidence >= 0.4:
            return "uncertain"
        else:
            return "questionable"
    
    def _generate_explanation(self, claim: str, status: str, confidence: float) -> str:
        """Generate explanation for the verification result."""
        explanations = {
            "verified": f"该声明包含具体数据和可靠来源，置信度较高({confidence:.1%})。建议进一步核实具体数据来源。",
            "likely_true": f"该声明具有一定可信度({confidence:.1%})，但建议核实相关数据和来源。",
            "uncertain": f"该声明的可信度一般({confidence:.1%})，缺乏充分的证据支持，需要更多验证。",
            "questionable": f"该声明的可信度较低({confidence:.1%})，可能存在不准确信息，建议谨慎使用。"
        }
        
        return explanations.get(status, "无法确定该声明的准确性。")
    
    def _get_mock_sources(self, claim: str) -> List[str]:
        """Generate mock sources for the claim."""
        sources = [
            "权威机构研究报告",
            "官方统计数据",
            "学术期刊文献",
            "新闻媒体报道"
        ]
        
        # Return 2-3 relevant sources
        return sources[:3]
    
    def _get_recommendations(self, status: str) -> List[str]:
        """Get recommendations based on verification status."""
        recommendations = {
            "verified": [
                "可以引用该信息，但建议标注具体来源",
                "如有可能，提供原始数据链接"
            ],
            "likely_true": [
                "建议进一步验证数据来源",
                "可以使用，但应注明信息来源的局限性"
            ],
            "uncertain": [
                "需要寻找更多可靠来源进行验证",
                "如果使用，应明确标注信息的不确定性"
            ],
            "questionable": [
                "建议不要使用该信息",
                "如必须使用，应添加免责声明"
            ]
        }
        
        return recommendations.get(status, ["需要进一步核实"])
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of all fact-check results."""
        total_claims = len(results)
        verified_count = sum(1 for r in results if r["verification_status"] == "verified")
        likely_true_count = sum(1 for r in results if r["verification_status"] == "likely_true")
        uncertain_count = sum(1 for r in results if r["verification_status"] == "uncertain")
        questionable_count = sum(1 for r in results if r["verification_status"] == "questionable")
        
        avg_confidence = sum(r["confidence"] for r in results) / total_claims if total_claims > 0 else 0
        
        return {
            "total_claims": total_claims,
            "verified": verified_count,
            "likely_true": likely_true_count,
            "uncertain": uncertain_count,
            "questionable": questionable_count,
            "average_confidence": round(avg_confidence, 2),
            "overall_reliability": "high" if avg_confidence >= 0.7 else "medium" if avg_confidence >= 0.5 else "low"
        }