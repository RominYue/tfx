# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for tfx.orchestration.portable.importer_node_handler."""
import os

import tensorflow as tf
from tfx.orchestration import metadata
from tfx.orchestration.portable import importer_node_handler
from tfx.orchestration.portable import test_utils
from tfx.proto.orchestration import pipeline_pb2


class ImporterNodeHandlerTest(test_utils.TfxTest):

  def setUp(self):
    super().setUp()
    pipeline_root = os.path.join(
        os.environ.get('TEST_UNDECLARED_OUTPUTS_DIR', self.get_temp_dir()),
        self.id())

    # Makes sure multiple connections within a test always connect to the same
    # MLMD instance.
    metadata_path = os.path.join(pipeline_root, 'metadata', 'metadata.db')
    connection_config = metadata.sqlite_metadata_connection_config(
        metadata_path)
    connection_config.sqlite.SetInParent()
    self._mlmd_connection = metadata.Metadata(
        connection_config=connection_config)
    self._testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')

    # Sets up pipelines
    pipeline = pipeline_pb2.Pipeline()
    self.load_proto_from_text(
        os.path.join(
            os.path.dirname(__file__), 'testdata',
            'pipeline_for_launcher_test.pbtxt'), pipeline)
    self._pipeline_info = pipeline.pipeline_info
    self._pipeline_runtime_spec = pipeline.runtime_spec

    # Extracts components
    self._importer = pipeline.nodes[3].pipeline_node

  def testLauncher_importer_mode_reimport_enabled(self):
    handler = importer_node_handler.ImporterNodeHandler()
    execution_metadata = handler.run(
        mlmd_connection=self._mlmd_connection,
        pipeline_node=self._importer,
        pipeline_info=self._pipeline_info,
        pipeline_runtime_spec=self._pipeline_runtime_spec)

    with self._mlmd_connection as m:
      [artifact] = m.store.get_artifacts_by_type('Schema')
      self.assertProtoPartiallyEquals(
          """
          id: 1
          type_id: 4
          uri: "my_url"
          custom_properties {
            key: "int_custom_property"
            value {
              int_value: 123
            }
          }
          custom_properties {
            key: "str_custom_property"
            value {
              string_value: "abc"
            }
          }
          state: LIVE""",
          artifact,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])
      [execution] = m.store.get_executions_by_id([execution_metadata.id])
      self.assertProtoPartiallyEquals(
          """
          id: 1
          type_id: 3
          last_known_state: COMPLETE
          custom_properties {
            key: "artifact_uri"
            value {
              string_value: "my_url"
            }
          }
          custom_properties {
            key: "reimport"
            value {
              int_value: 1
            }
          }
          """,
          execution,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])

    execution_metadata = handler.run(
        mlmd_connection=self._mlmd_connection,
        pipeline_node=self._importer,
        pipeline_info=self._pipeline_info,
        pipeline_runtime_spec=self._pipeline_runtime_spec)
    with self._mlmd_connection as m:
      new_artifact = m.store.get_artifacts_by_type('Schema')[1]
      self.assertProtoPartiallyEquals(
          """
          id: 2
          type_id: 4
          uri: "my_url"
          custom_properties {
            key: "int_custom_property"
            value {
              int_value: 123
            }
          }
          custom_properties {
            key: "str_custom_property"
            value {
              string_value: "abc"
            }
          }
          state: LIVE""",
          new_artifact,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])
      [execution] = m.store.get_executions_by_id([execution_metadata.id])
      self.assertProtoPartiallyEquals(
          """
          id: 2
          type_id: 3
          last_known_state: COMPLETE
          custom_properties {
            key: "artifact_uri"
            value {
              string_value: "my_url"
            }
          }
          custom_properties {
            key: "reimport"
            value {
              int_value: 1
            }
          }
          """,
          execution,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])

  def testLauncher_importer_mode_reimport_disabled(self):
    self._importer.parameters.parameters['reimport'].field_value.int_value = 0
    handler = importer_node_handler.ImporterNodeHandler()
    execution_metadata = handler.run(
        mlmd_connection=self._mlmd_connection,
        pipeline_node=self._importer,
        pipeline_info=self._pipeline_info,
        pipeline_runtime_spec=self._pipeline_runtime_spec)

    with self._mlmd_connection as m:
      [artifact] = m.store.get_artifacts_by_type('Schema')
      self.assertProtoPartiallyEquals(
          """
          id: 1
          type_id: 4
          uri: "my_url"
          custom_properties {
            key: "int_custom_property"
            value {
              int_value: 123
            }
          }
          custom_properties {
            key: "str_custom_property"
            value {
              string_value: "abc"
            }
          }
          state: LIVE""",
          artifact,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])
      [execution] = m.store.get_executions_by_id([execution_metadata.id])
      self.assertProtoPartiallyEquals(
          """
          id: 1
          type_id: 3
          last_known_state: COMPLETE
          custom_properties {
            key: "artifact_uri"
            value {
              string_value: "my_url"
            }
          }
          custom_properties {
            key: "reimport"
            value {
              int_value: 0
            }
          }
          """,
          execution,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])

    execution_metadata = handler.run(
        mlmd_connection=self._mlmd_connection,
        pipeline_node=self._importer,
        pipeline_info=self._pipeline_info,
        pipeline_runtime_spec=self._pipeline_runtime_spec)
    with self._mlmd_connection as m:
      # No new Schema is produced.
      self.assertLen(m.store.get_artifacts_by_type('Schema'), 1)
      [execution] = m.store.get_executions_by_id([execution_metadata.id])
      self.assertProtoPartiallyEquals(
          """
          id: 2
          type_id: 3
          last_known_state: COMPLETE
          custom_properties {
            key: "artifact_uri"
            value {
              string_value: "my_url"
            }
          }
          custom_properties {
            key: "reimport"
            value {
              int_value: 0
            }
          }
          """,
          execution,
          ignored_fields=[
              'create_time_since_epoch', 'last_update_time_since_epoch'
          ])


if __name__ == '__main__':
  tf.test.main()
