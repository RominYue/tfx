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
r"""This module defines the binary used to run PythonExecutorOperator in Tflex.

Example:

python_executor_binary
--tfx_execution_info_b64=ChcKEAgBEgxnZW5lcmljX3R5cGUSA2ZvbyoPCg0KAnAxEgcKBRoDYmFy
\
--tfx_python_class_executable_spec_b64=ChcKEAgBEgxnZW5lcmljX3R5cGUSA2ZvbyoPCg0KAnAxEgcKBRoDYmFy
\
--alsologtostderr

This binary is intended to be called by the Tflex IR based launcher and should
not be called directly.

"""
from absl import app
from absl import flags
from absl import logging

from tfx.dsl.io import fileio
from tfx.orchestration import metadata
from tfx.orchestration.portable import data_types
from tfx.orchestration.portable import python_driver_operator
from tfx.orchestration.portable import python_executor_operator
from tfx.orchestration.python_execution_binary import python_execution_binary_utils
from tfx.proto.orchestration import driver_output_pb2
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration import execution_result_pb2
from google.protobuf import text_format

FLAGS = flags.FLAGS

EXECUTION_INVOCATION_FLAG = flags.DEFINE_string(
    'tfx_execution_info_b64', None, 'url safe base64 encoded binary '
    'tfx.orchestration.ExecutionInvocation proto')
EXECUTABLE_SPEC_FLAG = flags.DEFINE_string(
    'tfx_python_class_executable_spec_b64', None,
    'tfx.orchestration.executable_spec.PythonClassExecutableSpec proto')
MLMD_CONNECTION_CONFIG_FLAG = flags.DEFINE_string(
    'tfx_mlmd_connection_config_b64', None,
    'wrapper proto containing MLMD connection config. If being set, this'
    'indicates a driver execution')


def _run_executor(
    executable_spec: executable_spec_pb2.PythonClassExecutableSpec,
    execution_info: data_types.ExecutionInfo
) -> execution_result_pb2.ExecutorOutput:
  operator = python_executor_operator.PythonExecutorOperator(executable_spec)
  return operator.run_executor(execution_info)


def _run_driver(
    executable_spec: executable_spec_pb2.PythonClassExecutableSpec,
    mlmd_connection_config: metadata.ConnectionConfigType,
    execution_info: data_types.ExecutionInfo) -> driver_output_pb2.DriverOutput:
  operator = python_driver_operator.PythonDriverOperator(
      executable_spec, metadata.Metadata(mlmd_connection_config))
  return operator.run_driver(execution_info)


def main(_):

  flags.mark_flag_as_required(EXECUTION_INVOCATION_FLAG.name)
  flags.mark_flag_as_required(EXECUTABLE_SPEC_FLAG.name)

  execution_info = python_execution_binary_utils.deserialize_execution_info(
      EXECUTION_INVOCATION_FLAG.value)
  python_class_executable_spec = (
      python_execution_binary_utils.deserialize_executable_spec(
          EXECUTABLE_SPEC_FLAG.value))
  logging.info('execution_info = %r\n', execution_info)
  logging.info('python_class_executable_spec = %s\n',
               text_format.MessageToString(python_class_executable_spec))

  # MLMD connection config being set indicates a driver execution instead of an
  # executor execution as accessing MLMD is not supported for executors.
  if MLMD_CONNECTION_CONFIG_FLAG.value:
    mlmd_connection_config = (
        python_execution_binary_utils.deserialize_mlmd_connection_config(
            MLMD_CONNECTION_CONFIG_FLAG.value))
    run_result = _run_driver(python_class_executable_spec,
                             mlmd_connection_config, execution_info)
  else:
    run_result = _run_executor(python_class_executable_spec, execution_info)

  if run_result:
    with fileio.open(execution_info.execution_output_uri, 'wb') as f:
      f.write(run_result.SerializeToString())


if __name__ == '__main__':
  app.run(main)
