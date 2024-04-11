
set(TT_LIB_SRCS
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/type_caster.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_composite_ops.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_backward_ops.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_pytensor.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_dm_ops.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_custom_bmm_ops.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/csrc/tt_lib_bindings_tensor_xary_ops.cpp
)

add_subdirectory(${CMAKE_SOURCE_DIR}/tt_metal/third_party/pybind11 ${CMAKE_BINARY_DIR}/pybind11)

pybind11_add_module(tt_lib MODULE ${TT_LIB_SRCS})

target_link_libraries(tt_lib PUBLIC tt_eager tt_metal)
target_include_directories(tt_lib PUBLIC
                        ${UMD_HOME}
                        ${CMAKE_SOURCE_DIR}
                        ${CMAKE_SOURCE_DIR}/tt_metal
                        ${CMAKE_CURRENT_SOURCE_DIR}
)
target_compile_options(tt_lib PUBLIC ${COMPILE_OPTIONS} -fno-var-tracking -Wno-int-to-pointer-cast)
target_link_directories(tt_lib PUBLIC
    ${CMAKE_BINARY_DIR}/tt_eager
    ${CMAKE_BINARY_DIR}/tt_metal
    ${CMAKE_BINARY_DIR}/python_env/lib/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}/site-packages)
# -Wno-int-to-pointer-cast  -fno-var-tracking <- why no variable tracking?