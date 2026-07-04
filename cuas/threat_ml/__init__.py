"""RADAR/RF 관측 기반 threat_level(LOW/MEDIUM/HIGH) 사전분류기.

Desktop의 sensor_threat_classifier 프로젝트(규칙 기반 사전필터 + 정규화 ML 재분류)를
cuas_simulator에 이식한 독립 모듈. IR/광학 센서는 이 프로젝트에 없으므로 사용하지 않고,
cuas.simulator/cuas.pipeline/cuas.engine이 이미 생성·산출하는 RADAR·RF 관측값과
위협평가 결과만으로 학습 데이터를 구성한다. engine.py/pipeline.py/simulator.py는
감싸서 재사용할 뿐 수정하지 않는다.
"""
