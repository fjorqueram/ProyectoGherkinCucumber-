"""
Utilidades para limpiar y normalizar texto corrupto.
Sistema inteligente que aprende patrones de corrupción automáticamente.
"""
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
from loguru import logger as log


class TextCleaner:
    """Limpia texto corrupto con detección automática de patrones."""
    
    # Archivo de configuración de correcciones aprendidas
    CORRECTIONS_FILE = Path(__file__).parent.parent / "data" / "text_corrections.json"
    
    # Diccionario en memoria (se carga/guarda dinámicamente)
    _corrections: Dict[str, str] = {}
    
    # Diccionario de palabras españolas válidas (cache)
    _valid_words: set = set()
    
    # Palabras comunes en español para validación
    SPANISH_COMMON_WORDS = {
        'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'por',
        'con', 'su', 'para', 'está', 'son', 'del', 'las', 'un', 'por', 'con',
        'ha', 'hay', 'sido', 'siendo', 'ser', 'está', 'estamos', 'están',
        'usuario', 'clic', 'archivo', 'fila', 'tabla', 'descarga', 'carga',
        'accede', 'cuando', 'dado', 'entonces', 'gherkin', 'feature'
    }
    
    @classmethod
    def _load_corrections(cls) -> Dict[str, str]:
        """Carga correcciones desde archivo si existe."""
        if cls._corrections:
            return cls._corrections
        
        if cls.CORRECTIONS_FILE.exists():
            try:
                with open(cls.CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
                    cls._corrections = json.load(f)
                log.debug(f"Loaded {len(cls._corrections)} learned corrections")
            except Exception as e:
                log.warning(f"Could not load corrections: {e}")
                cls._corrections = {}
        
        return cls._corrections
    
    @classmethod
    def _save_corrections(cls) -> None:
        """Guarda correcciones en archivo."""
        try:
            cls.CORRECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(cls.CORRECTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(cls._corrections, f, ensure_ascii=False, indent=2)
            log.debug(f"Saved {len(cls._corrections)} learned corrections")
        except Exception as e:
            log.warning(f"Could not save corrections: {e}")
    
    @staticmethod
    def _remove_duplicate_chars(text: str) -> str:
        """Remueve caracteres duplicados problemáticos."""
        # Vocales duplicadas (excepto casos legítimos)
        text = re.sub(r'([aeiouáéíóú])\1{2,}', r'\1', text, flags=re.IGNORECASE)
        
        # Consonantes duplicadas (excepto ll, rr, ss en español)
        for char in 'bcdfghjkmnptvwxyz':
            if char not in ['l', 'r', 's']:
                text = re.sub(f'{char}{{2,}}', char, text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def _find_similar_word(word: str, candidates: List[str], threshold: float = 0.75) -> str:
        """Encuentra la palabra más similar en una lista."""
        best_match = ""
        best_ratio = threshold
        
        for candidate in candidates:
            ratio = SequenceMatcher(None, word.lower(), candidate.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = candidate
        
        return best_match
    
    @classmethod
    def _auto_detect_corrections(cls, text: str) -> Dict[str, str]:
        """
        Detecta automáticamente palabras corruptas y sugiere correcciones.
        
        Returns:
            Dict con correcciones detectadas
        """
        detected = {}
        
        # Palabras españolas conocidas + comunes
        known_words = cls.SPANISH_COMMON_WORDS.copy()
        
        # Palabras del texto que parecen válidas
        words_in_text = re.findall(r'\b[a-záéíóúñ]+\b', text, re.IGNORECASE)
        
        for word in set(words_in_text):
            word_lower = word.lower()
            
            # Skip palabras muy cortas o ya conocidas
            if len(word) < 3 or word_lower in known_words:
                continue
            
            # Detectar patrones de corrupción
            
            # 1. Palabra con vocales duplicadas sospechosas
            if re.search(r'([aeiouáéíóú])\1{2,}', word, re.IGNORECASE):
                fixed = cls._remove_duplicate_chars(word)
                if fixed and fixed != word and fixed.lower() not in [w.lower() for w in known_words]:
                    detected[word] = fixed
                    continue
            
            # 2. Palabra que empieza con consonante duplicada
            if re.match(r'^([bcdfghjkmnptvwxyz])\1', word, re.IGNORECASE):
                fixed = re.sub(r'^([bcdfghjkmnptvwxyz])\1', r'\1', word, flags=re.IGNORECASE)
                if fixed and fixed != word:
                    detected[word] = fixed
                    continue
            
            # 3. Palabra que termina con consonante duplicada
            if re.search(r'([bcdfghjkmnptvwxyz])\1$', word, re.IGNORECASE):
                fixed = re.sub(r'([bcdfghjkmnptvwxyz])\1$', r'\1', word, flags=re.IGNORECASE)
                if fixed and fixed != word:
                    detected[word] = fixed
                    continue
            
            # 4. Buscar similar en palabras conocidas (typo/corrupción)
            if len(word) > 4:
                similar = cls._find_similar_word(word, list(known_words), threshold=0.65)
                if similar:  # Validar que no es vacío
                    detected[word] = similar
        
        return detected
    
    @classmethod
    def clean(cls, text: str, auto_learn: bool = True) -> str:
        """
        Limpia texto corrupto usando reglas aprendidas + detección automática.
        
        Args:
            text: Texto a limpiar
            auto_learn: Si True, aprende nuevas correcciones detectadas
            
        Returns:
            Texto limpiado
        """
        if not text:
            return text
        
        cleaned = text
        
        # 1. Aplicar correcciones ya aprendidas
        corrections = cls._load_corrections()
        for corrupt, fixed in corrections.items():
            cleaned = cleaned.replace(corrupt, fixed)
        
        # 2. Detección automática de nuevas corruptelas
        new_corrections = cls._auto_detect_corrections(cleaned)
        
        if new_corrections and auto_learn:
            log.debug(f"Auto-detected corrections: {new_corrections}")
            
            # Aplicar y guardar
            for corrupt, fixed in new_corrections.items():
                cleaned = cleaned.replace(corrupt, fixed)
                cls._corrections[corrupt] = fixed
            
            cls._save_corrections()
        else:
            # Solo aplicar sin guardar
            for corrupt, fixed in new_corrections.items():
                cleaned = cleaned.replace(corrupt, fixed)
        
        # 3. Remover duplicados residuales
        cleaned = cls._remove_duplicate_chars(cleaned)
        
        # 4. Normalizar espacios
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        
        # 5. Normalizar puntuación
        cleaned = re.sub(r'\s+([,.;:!?])', r'\1', cleaned)
        
        # 6. Remover caracteres inválidos
        cleaned = ''.join(c for c in cleaned if ord(c) >= 32 or c in '\n\t\r')
        
        # 7. Normalizar saltos de línea
        cleaned = re.sub(r'\n{2,}', '\n', cleaned)
        
        return cleaned.strip()