# Low-Confidence Output Handling Runbook
**Day 8: Operational Procedures for Quality Assurance**

**Version**: 1.0  
**Last Updated**: November 19, 2025  
**Audience**: Content Reviewers, QA Teams, Operations

---

## 📋 Overview

This runbook defines procedures for handling AI-generated content that the system flags as **low-confidence** or **high hallucination risk**. These outputs require special attention to maintain quality standards.

---

## 🎯 Detection Thresholds

### **Confidence Score Classification**

| Confidence Score | Classification | Action Required |
|-----------------|----------------|-----------------|
| **0.8 - 1.0** | ✅ High Confidence | Standard review process |
| **0.7 - 0.79** | ⚠️ Medium Confidence | Enhanced review required |
| **0.5 - 0.69** | 🟡 Low Confidence | Senior reviewer approval required |
| **< 0.5** | 🔴 Very Low Confidence | **Block automatic publication** |

### **Hallucination Risk Classification**

| Risk Level | Support Score | Detection Criteria | Action |
|-----------|---------------|-------------------|--------|
| **Low** | ≥ 0.7 | Well-grounded in RAG context | Standard workflow |
| **Medium** | 0.5 - 0.69 | Partially supported claims | Flag for review |
| **High** | < 0.5 | Unsupported or fabricated claims | **Immediate escalation** |

---

## 🚨 Detection Triggers

The system automatically flags outputs when:

1. **Confidence score < 0.7** - Low quality signal
2. **Hallucination risk = "high"** - Unsupported claims detected
3. **Support score < 0.6** - Less than 60% of sentences grounded in RAG
4. **No RAG context available** - Generation without retrieval support
5. **Body length < 200 chars** - Insufficient content generated

---

## 📊 Response Procedures

### **1. Automatic Flagging in API Response**

Low-confidence outputs include warning indicators in the API response:

```json
{
  "content_type": "blog",
  "topic": "advanced quantum computing",
  "headline": "The Future of Quantum Computing",
  "body": "...",
  "confidence_score": 0.58,           // 🟡 LOW CONFIDENCE
  "hallucination_risk": "high",       // 🔴 HIGH RISK
  "quality_metrics": {
    "hallucination_support_score": 0.45,
    "unsupported_claims_sample": [
      "Quantum computers can solve any problem instantly",
      "All encryption will be broken by 2026"
    ]
  }
}
```

**Recognition**: Any output with `confidence_score < 0.7` or `hallucination_risk = "high"/"medium"`

---

### **2. Human Review Queue Routing**

**Streamlit UI Behavior**:
- Low-confidence outputs automatically flagged with ⚠️ badge
- Orange/red color coding for warning levels
- Detailed quality metrics displayed prominently
- Review actions automatically require additional documentation

**Queue Priority**:
1. **Very Low Confidence (< 0.5)**: Top priority, immediate review
2. **High Hallucination Risk**: Urgent review within 1 hour
3. **Low Confidence (0.5-0.69)**: Review within 4 hours
4. **Medium Confidence (0.7-0.79)**: Review within 24 hours

---

### **3. Review Actions by Confidence Level**

#### **High Confidence (0.8-1.0)** ✅
- **Action**: Standard approval workflow
- **Approver**: Any trained reviewer
- **Timeframe**: Standard SLA
- **Publication**: Automatic after approval

#### **Medium Confidence (0.7-0.79)** ⚠️
- **Action**: Enhanced review with fact-checking
- **Approver**: Experienced reviewer (>3 months)
- **Timeframe**: Priority review (< 4 hours)
- **Publication**: Manual approval required
- **Validation**: Cross-reference claims with source documents

#### **Low Confidence (0.5-0.69)** 🟡
- **Action**: Senior reviewer escalation
- **Approver**: Senior reviewer or subject matter expert
- **Timeframe**: Urgent (< 1 hour)
- **Publication**: **Hold until senior approval**
- **Additional Steps**:
  - Manual fact-checking of all claims
  - Comparison with RAG source documents
  - Edit to ground unsupported claims
  - Resubmit for confidence recalculation

#### **Very Low Confidence (< 0.5)** 🔴
- **Action**: **Block automatic publication**
- **Approver**: Team lead or QA manager
- **Timeframe**: Immediate escalation
- **Publication**: **Do NOT publish without complete rewrite**
- **Root Cause Analysis**:
  - Insufficient RAG context?
  - Prompt needs refinement?
  - Topic outside model's knowledge?
  - Model hallucinating consistently?

---

### **4. Escalation Matrix**

| Scenario | Escalate To | Action |
|----------|------------|--------|
| Confidence < 0.5 | Team Lead | Block publication, investigate root cause |
| Hallucination Risk = "high" | Senior Reviewer | Fact-check all claims, edit or reject |
| Multiple low-confidence outputs (>20% of batch) | QA Manager | Review prompt templates and model performance |
| Repeated hallucinations on same topic | ML Engineer | Update RAG data or retrain model |
| Customer complaint about inaccurate content | Incident Manager | Immediate content audit and removal if needed |

---

### **5. Approval Workflow**

```
┌─────────────────────────────────────────────────────────────┐
│                     CONTENT GENERATION                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Confidence   │
                  │ Calculation  │
                  └──────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ High     │   │ Medium   │   │ Low/Very │
   │ (≥0.8)   │   │ (0.7-0.8)│   │ Low(<0.7)│
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Standard │   │ Enhanced │   │ Senior   │
   │ Review   │   │ Review   │   │ Escalate │
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        └──────┬───────┴──────────────┘
               │
               ▼
        ┌──────────────┐
        │ APPROVE/     │
        │ REJECT/      │
        │ EDIT         │
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐
        │ Publication  │
        │ or Hold      │
        └──────────────┘
```

---

## 🔍 Review Checklist

### **For All Low-Confidence Outputs**

- [ ] Review confidence score and hallucination risk level
- [ ] Examine unsupported claims sample in `quality_metrics`
- [ ] Verify support score: `hallucination_support_score`
- [ ] Check if RAG documents were used: `rag_documents_used`
- [ ] Cross-reference claims against retrieved RAG context
- [ ] Identify factual errors or fabricated information
- [ ] Assess tone and style appropriateness
- [ ] Verify all required fields present (headline, body, CTA)

### **Additional Checks for High Hallucination Risk**

- [ ] Line-by-line fact verification
- [ ] External source validation (if applicable)
- [ ] Comparison with authoritative documentation
- [ ] Legal/compliance review for sensitive topics
- [ ] Consult subject matter expert if available

---

## 📝 Documentation Requirements

### **Rejection Documentation**

When rejecting low-confidence content, document:

1. **Specific issues identified** (factual errors, unsupported claims, tone problems)
2. **Evidence** (cite RAG documents or external sources that contradict claims)
3. **Severity** (minor inaccuracies vs. major fabrications)
4. **Recommendation** (edit, regenerate, or change approach)

**Example**:
```
REJECTION REASON:
- Claim: "All encryption will be broken by 2026"
  Issue: Unsupported and factually incorrect
  Evidence: No RAG documents support this timeline
  Severity: HIGH - Misinformation
  
- Claim: "Quantum computers can solve any problem instantly"
  Issue: Overgeneralization, misleading
  Evidence: RAG context discusses specific use cases only
  Severity: MEDIUM - Misleading
  
Recommendation: Regenerate with more conservative claims grounded in RAG context
```

### **Edit Documentation**

When editing low-confidence content, log:

1. **Original problematic sections** (before editing)
2. **Changes made** (specific edits to improve accuracy)
3. **Sources used** (RAG documents or external references)
4. **New confidence assessment** (subjective quality rating post-edit)

---

## 📈 Feedback Loop

### **Weekly Analysis**

QA team conducts weekly review of low-confidence outputs:

1. **Aggregate Statistics**:
   - Total generations vs. low-confidence count
   - Low-confidence rate by content type
   - Common hallucination patterns
   - Average confidence scores by topic category

2. **Pattern Identification**:
   - Which topics consistently trigger low confidence?
   - Which content types have highest hallucination risk?
   - Are certain tones more problematic?
   - Time-of-day or load correlations?

3. **Improvement Actions**:
   - Update prompt templates for problematic content types
   - Add more RAG documents for weak topic areas
   - Adjust confidence calculation thresholds
   - Retrain model if systemic issues identified

### **Monthly Reporting**

Generate monthly report including:

- Low-confidence rate trend (target: < 15%)
- Hallucination incident count (target: 0 published)
- Average confidence score by content type
- Reviewer feedback themes
- Prompt template updates implemented
- RAG data quality improvements

---

## 🛠️ Technical Integration

### **API Response Handling**

Client applications should check confidence scores:

```python
import requests

response = requests.post("http://localhost:8000/v1/generate/content", json={
    "content_type": "blog",
    "topic": "quantum computing",
    "tone": "professional"
})

result = response.json()

# Check confidence
if result['confidence_score'] < 0.7:
    print(f"⚠️ LOW CONFIDENCE: {result['confidence_score']:.2f}")
    print(f"Hallucination Risk: {result['hallucination_risk']}")
    
    # Route to human review queue
    send_to_review_queue(result)
    
elif result['confidence_score'] < 0.8:
    print(f"⚠️ MEDIUM CONFIDENCE: {result['confidence_score']:.2f}")
    
    # Enhanced automated checks
    run_additional_validation(result)
    
else:
    print(f"✅ HIGH CONFIDENCE: {result['confidence_score']:.2f}")
    
    # Proceed with standard workflow
    publish_content(result)
```

### **Streamlit UI Display**

Review interface should prominently display:

```python
# In ui/review_app.py

if confidence_score < 0.5:
    st.error(f"🔴 VERY LOW CONFIDENCE: {confidence_score:.2f} - BLOCK PUBLICATION")
elif confidence_score < 0.7:
    st.warning(f"🟡 LOW CONFIDENCE: {confidence_score:.2f} - Requires senior approval")
elif confidence_score < 0.8:
    st.info(f"⚠️ MEDIUM CONFIDENCE: {confidence_score:.2f} - Enhanced review needed")
else:
    st.success(f"✅ HIGH CONFIDENCE: {confidence_score:.2f}")

# Display quality metrics
st.subheader("Quality Metrics")
st.write(f"Hallucination Risk: {hallucination_risk}")
st.write(f"Support Score: {quality_metrics['hallucination_support_score']:.2f}")
st.write(f"Supported Sentences: {quality_metrics['supported_sentences']}/{quality_metrics['total_sentences']}")

if quality_metrics.get('unsupported_claims_sample'):
    st.warning("Unsupported Claims Detected:")
    for claim in quality_metrics['unsupported_claims_sample']:
        st.write(f"  • {claim}")
```

---

## 🎓 Reviewer Training

### **Required Training for Reviewers**

1. **Understanding Confidence Scores**: What they mean and how they're calculated
2. **Hallucination Detection**: How to identify unsupported claims
3. **RAG Context Review**: How to cross-reference claims with retrieved documents
4. **Escalation Procedures**: When and how to escalate
5. **Documentation Standards**: How to properly log rejection/edit reasons

### **Certification Levels**

- **Junior Reviewer**: Can approve high-confidence outputs (≥0.8)
- **Experienced Reviewer**: Can approve medium-confidence outputs (≥0.7)
- **Senior Reviewer**: Can approve low-confidence outputs (≥0.5)
- **Team Lead**: Final authority on very low confidence (< 0.5)

---

## 📞 Contact & Escalation

| Issue Type | Contact | Response Time |
|-----------|---------|---------------|
| Low-confidence content | Senior Reviewer | 1 hour |
| Very low confidence | Team Lead | 30 minutes |
| System-wide quality issues | QA Manager | Immediate |
| Hallucination incident (published) | Incident Manager | Immediate |
| Technical failures | ML Engineer | 2 hours |

---

## 📚 Related Documentation

- **Architecture**: `docs/architecture/AGENT_ARCHITECTURE.md`
- **Optimization Guide**: `docs/guides/OPTIMIZATION_GUIDE.md`
- **API Reference**: `docs/api/API_REFERENCE.md`
- **Review System Guide**: `DAY8_REVIEW_SYSTEM_GUIDE.md`

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-19 | Initial runbook created for Day 8 implementation |

---

**Last Updated**: November 19, 2025  
**Status**: ✅ Active  
**Next Review**: December 19, 2025
