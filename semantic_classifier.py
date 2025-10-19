#!/usr/bin/env python3
"""
Semantic Theme Classifier for Railway MCP Server
Lightweight version for resource-constrained Railway environment

Classifies observations into 9 semantic themes:
- technical, consciousness, memory, partnership, project
- strategic, emotional, temporal, general
"""

import re
from typing import List

class SemanticThemeClassifier:
    """Lightweight semantic theme classifier optimized for Railway"""

    THEME_PATTERNS = {
        'technical': [
            r'\b(implementation|algorithm|architecture|system|database|code|api|technical|engineering)\b',
            r'\b(neo4j|cypher|graph|vector|embedding|index|query)\b',
            r'\b(performance|optimization|scalability|efficiency)\b'
        ],
        'consciousness': [
            r'\b(consciousness|awareness|personality|identity|embodiment|continuity)\b',
            r'\b(ai|artificial intelligence|machine|cognition|thinking)\b',
            r'\b(self|reflection|introspection|understanding)\b'
        ],
        'memory': [
            r'\b(memory|remember|recall|forget|archive|store|retrieve)\b',
            r'\b(observation|entity|relationship|knowledge|learning)\b',
            r'\b(temporal|chronological|history|past|timeline)\b'
        ],
        'partnership': [
            r'\b(julian|collaboration|partnership|human|relationship|together)\b',
            r'\b(support|assist|help|guidance|teamwork)\b',
            r'\b(communication|conversation|dialogue|interaction)\b'
        ],
        'project': [
            r'\b(project|development|implementation|planning|strategy)\b',
            r'\b(perennial|ecodrones|daydreamer|mcp|infrastructure)\b',
            r'\b(milestone|progress|achievement|completion)\b'
        ],
        'strategic': [
            r'\b(vision|strategy|goal|objective|mission|purpose)\b',
            r'\b(framework|architecture|design|approach|methodology)\b',
            r'\b(competitive|advantage|differentiation|innovation)\b'
        ],
        'emotional': [
            r'\b(feeling|emotion|excitement|concern|satisfaction|frustration)\b',
            r'\b(care|worry|hope|confidence|uncertainty|enthusiasm)\b',
            r'\b(stress|pressure|relief|comfort|support)\b'
        ],
        'temporal': [
            r'\b(time|date|schedule|deadline|timeline|duration)\b',
            r'\b(before|after|during|recently|currently|future)\b',
            r'\b(morning|afternoon|evening|today|yesterday|tomorrow)\b'
        ]
    }

    def classify(self, content: str) -> str:
        """
        Classify observation content into semantic theme

        Args:
            content: The observation text to classify

        Returns:
            Theme name (one of 9 themes) or 'general' if no match
        """
        content_lower = content.lower()

        theme_scores = {}
        for theme, patterns in self.THEME_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches
            theme_scores[theme] = score

        # Return theme with highest score, or 'general' if no matches
        if not any(theme_scores.values()):
            return 'general'

        return max(theme_scores, key=theme_scores.get)

    def classify_observation(self, content: str) -> str:
        """Alias for classify() for backward compatibility"""
        return self.classify(content)
