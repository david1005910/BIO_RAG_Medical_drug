"""Neo4j 그래프 데이터 동기화 스크립트"""
import asyncio
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.external.neo4j_client import Neo4jClient
from app.models.disease import Disease
from app.models.drug import Drug
from app.services.neo4j_service import Neo4jService

# 증상 키워드 (efficacy 필드에서 추출)
SYMPTOM_KEYWORDS = [
    "두통", "발열", "통증", "기침", "가래", "콧물", "코막힘", "재채기",
    "인후통", "목구멍통증", "오한", "근육통", "관절통", "요통", "치통",
    "신경통", "월경통", "생리통", "속쓰림", "소화불량", "구역", "구토",
    "복통", "설사", "변비", "위부팽만감", "식욕부진", "어지러움",
    "졸음", "피로", "알레르기", "두드러기", "가려움", "발진",
    "부종", "염증", "감기", "비염", "결막염",
]


def extract_symptoms(efficacy: str) -> List[str]:
    """효능 텍스트에서 증상 추출"""
    if not efficacy:
        return []

    symptoms = []
    text = efficacy.lower()

    for symptom in SYMPTOM_KEYWORDS:
        if symptom in text:
            symptoms.append(symptom)

    return list(set(symptoms))


def extract_drug_names(text: str) -> List[str]:
    """텍스트에서 약물명 추출 (상호작용 필드용)"""
    if not text:
        return []

    # 간단한 약물명 패턴 매칭
    patterns = [
        r"([가-힣]+정)",  # ~정
        r"([가-힣]+캡슐)",  # ~캡슐
        r"([가-힣]+시럽)",  # ~시럽
    ]

    drug_names = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        drug_names.extend(matches)

    return list(set(drug_names))


async def sync_drug_nodes(
    db_session,
    neo4j_service: Neo4jService,
) -> int:
    """Drug 노드 동기화"""
    print("\n📦 Drug 노드 동기화 중...")

    result = await db_session.execute(select(Drug))
    drugs = result.scalars().all()

    count = 0
    for drug in drugs:
        success = await neo4j_service.create_drug_node(
            drug_id=drug.id,
            item_name=drug.item_name,
            entp_name=drug.entp_name,
            efficacy=drug.efficacy[:500] if drug.efficacy else None,
            category=None,  # 카테고리는 별도 추출 필요
        )
        if success:
            count += 1
            if count % 100 == 0:
                print(f"  - {count}개 완료...")

    print(f"  ✅ {count}개 Drug 노드 생성 완료")
    return count


async def sync_disease_nodes(
    db_session,
    neo4j_service: Neo4jService,
) -> int:
    """Disease 노드 동기화"""
    print("\n🏥 Disease 노드 동기화 중...")

    try:
        result = await db_session.execute(select(Disease))
        diseases = result.scalars().all()
    except Exception as e:
        print(f"  ⚠️ Disease 테이블 조회 실패: {e}")
        return 0

    count = 0
    for disease in diseases:
        success = await neo4j_service.create_disease_node(
            disease_id=disease.id,
            name=disease.name,
            name_en=getattr(disease, "name_en", None),
            category=getattr(disease, "category", None),
        )
        if success:
            count += 1

    print(f"  ✅ {count}개 Disease 노드 생성 완료")
    return count


async def sync_drug_symptoms(
    db_session,
    neo4j_service: Neo4jService,
) -> Tuple[int, int]:
    """Drug-Symptom (RELIEVES) 관계 동기화"""
    print("\n💊 Drug-Symptom 관계 동기화 중...")

    result = await db_session.execute(select(Drug))
    drugs = result.scalars().all()

    symptom_count = 0
    relation_count = 0
    symptoms_created: Set[str] = set()

    for drug in drugs:
        if not drug.efficacy:
            continue

        symptoms = extract_symptoms(drug.efficacy)
        for symptom in symptoms:
            # 증상 노드 생성
            if symptom not in symptoms_created:
                await neo4j_service.create_symptom_node(symptom)
                symptoms_created.add(symptom)
                symptom_count += 1

            # RELIEVES 관계 생성
            success = await neo4j_service.create_relieves_relationship(
                drug_id=drug.id,
                symptom_name=symptom,
                effectiveness=0.7,  # 기본값
            )
            if success:
                relation_count += 1

    print(f"  ✅ {symptom_count}개 Symptom 노드, {relation_count}개 RELIEVES 관계 생성 완료")
    return symptom_count, relation_count


async def sync_drug_interactions(
    db_session,
    neo4j_service: Neo4jService,
) -> int:
    """Drug-Drug (INTERACTS_WITH) 관계 동기화"""
    print("\n⚠️ Drug-Drug 상호작용 동기화 중...")

    result = await db_session.execute(select(Drug))
    drugs = result.scalars().all()

    # 약물명 -> ID 매핑
    drug_name_to_id = {drug.item_name: drug.id for drug in drugs}

    count = 0
    for drug in drugs:
        if not drug.interaction:
            continue

        # 상호작용 텍스트에서 다른 약물명 추출
        mentioned_drugs = extract_drug_names(drug.interaction)

        for mentioned in mentioned_drugs:
            if mentioned in drug_name_to_id and drug_name_to_id[mentioned] != drug.id:
                success = await neo4j_service.create_interaction(
                    drug_id_1=drug.id,
                    drug_id_2=drug_name_to_id[mentioned],
                    interaction_type="caution",
                    severity=2,
                    description=drug.interaction[:200] if drug.interaction else None,
                )
                if success:
                    count += 1

    print(f"  ✅ {count}개 INTERACTS_WITH 관계 생성 완료")
    return count


async def sync_drug_disease_relationships(
    db_session,
    neo4j_service: Neo4jService,
) -> int:
    """Drug-Disease (TREATS) 관계 동기화"""
    print("\n🔗 Drug-Disease 관계 동기화 중...")

    try:
        result = await db_session.execute(select(Disease))
        diseases = result.scalars().all()
    except Exception:
        print("  ⚠️ Disease 테이블이 없습니다. 건너뜀...")
        return 0

    # 약물명 -> ID 매핑
    drug_result = await db_session.execute(select(Drug))
    drugs = drug_result.scalars().all()
    drug_name_to_id = {drug.item_name: drug.id for drug in drugs}

    count = 0
    for disease in diseases:
        related_drugs = getattr(disease, "related_drugs", None)
        if not related_drugs:
            continue

        # related_drugs가 JSON 배열이거나 콤마 구분 문자열일 수 있음
        if isinstance(related_drugs, str):
            drug_names = [d.strip() for d in related_drugs.split(",")]
        elif isinstance(related_drugs, list):
            drug_names = related_drugs
        else:
            continue

        for drug_name in drug_names:
            if drug_name in drug_name_to_id:
                success = await neo4j_service.create_treats_relationship(
                    drug_id=drug_name_to_id[drug_name],
                    disease_id=disease.id,
                    efficacy_level="primary",
                    evidence="from related_drugs field",
                )
                if success:
                    count += 1

    print(f"  ✅ {count}개 TREATS 관계 생성 완료")
    return count


async def sync_similar_drugs(
    db_session,
    neo4j_service: Neo4jService,
) -> int:
    """Similar drugs (SIMILAR_TO) 관계 동기화 - 같은 제조사 기준"""
    print("\n🔄 유사 약물 관계 동기화 중...")

    result = await db_session.execute(select(Drug))
    drugs = result.scalars().all()

    # 제조사별 그룹핑
    entp_groups = {}
    for drug in drugs:
        if drug.entp_name:
            if drug.entp_name not in entp_groups:
                entp_groups[drug.entp_name] = []
            entp_groups[drug.entp_name].append(drug)

    count = 0
    for entp_name, group_drugs in entp_groups.items():
        if len(group_drugs) < 2:
            continue

        # 같은 제조사 약물끼리 SIMILAR_TO 관계 생성
        for i, drug1 in enumerate(group_drugs):
            for drug2 in group_drugs[i + 1 :]:
                success = await neo4j_service.create_similar_to(
                    drug_id_1=drug1.id,
                    drug_id_2=drug2.id,
                    similarity_score=0.6,
                    similarity_type="same_manufacturer",
                )
                if success:
                    count += 1

    print(f"  ✅ {count}개 SIMILAR_TO 관계 생성 완료")
    return count


async def main():
    import os

    print("=" * 60)
    print("🔧 Neo4j 그래프 데이터 동기화")
    print("=" * 60)

    # 환경 변수에서 설정 로드
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./medical_rag.db",
    )
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_password:
        print("❌ NEO4J_PASSWORD 환경 변수가 설정되지 않았습니다.")
        print("   export NEO4J_PASSWORD=your_password")
        sys.exit(1)

    print(f"\n📊 Database: {database_url}")
    print(f"📊 Neo4j: {neo4j_uri}")

    # Neo4j 연결
    neo4j_client = Neo4jClient(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
    )

    connected = await neo4j_client.connect()
    if not connected:
        print("❌ Neo4j 연결 실패")
        sys.exit(1)

    # 스키마 생성
    await neo4j_client.create_constraints_and_indexes()

    neo4j_service = Neo4jService(client=neo4j_client)

    # PostgreSQL/SQLite 연결
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db_session:
        # 1. Drug 노드 동기화
        await sync_drug_nodes(db_session, neo4j_service)

        # 2. Disease 노드 동기화
        await sync_disease_nodes(db_session, neo4j_service)

        # 3. Drug-Symptom 관계 동기화
        await sync_drug_symptoms(db_session, neo4j_service)

        # 4. Drug-Drug 상호작용 동기화
        await sync_drug_interactions(db_session, neo4j_service)

        # 5. Drug-Disease 관계 동기화
        await sync_drug_disease_relationships(db_session, neo4j_service)

        # 6. 유사 약물 관계 동기화
        await sync_similar_drugs(db_session, neo4j_service)

    # 통계 출력
    stats = await neo4j_client.get_stats()
    print("\n" + "=" * 60)
    print("📊 동기화 완료 통계:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    print("=" * 60)

    # 연결 종료
    await neo4j_client.close()
    await engine.dispose()

    print("\n✅ Neo4j 그래프 동기화 완료!")


if __name__ == "__main__":
    asyncio.run(main())
